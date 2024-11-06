import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class NetvisorInvoiceExportMapper(Component):
    _name = "netvisor.invoice.export.mapper"
    _description = "Netvisor Invoice Export Mapper"
    _inherit = "base.export.mapper"
    _usage = "export.mapper"
    _apply_on = ["netvisor.invoice"]

    def export_invoice(self, backend, record):
        """
        Export invoice from Odoo to Netvisor
        :param backend: Netvisor backend record
        :param record: Account move record
        :return:
        """
        self._validate(record)

        if not record.netvisor_send:
            return _("Netvisor sending is disabled for this invoice")

        if record.amount_total_signed == 0:
            return _("Zero sum invoice. Skip sending")

        # Force record company for property fields
        company_id = False
        if record.company_id:
            company_id = record.company_id.id
            record = record.with_company(company_id)

        # Update partner information to Netvisor
        record.partner_id.action_netvisor_export_record(
            use_queue=False, company_id=company_id
        )
        if (
            record.partner_shipping_id
            and record.partner_id != record.partner_shipping_id
        ):
            record.partner_shipping_id.action_netvisor_export_record(
                use_queue=False, company_id=company_id
            )

        # Set correct states
        if record.reversed_entry_id and backend.auto_open_refunds:
            # Mark the to-be-created refund as open immediately
            record.netvisor_status = "open"
        elif record.state == "draft":
            record.netvisor_status = "unsent"
        elif record.state == "cancel":
            record.netvisor_status = "rejected"

        # Create a dict for dimensions items
        # Syntax {analytic_account_id: (analytic_plan_name, analytic_account_name)}
        analytic_accounts = self.env["account.analytic.account"].search([])
        dimensions = dict([(r.id, (r.plan_id.name, r.name)) for r in analytic_accounts])
        for line in record.invoice_line_ids:
            if line.analytic_distribution:
                for ad in line.analytic_distribution.values():
                    if ad != 100.0:
                        raise ValidationError(
                            _(
                                "Only 100% analytic distribution is supported by Netvisor!"
                            )
                        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor.netvisor_salesinvoice",
            {"invoice": record, "backend": backend, "dimensions": dimensions},
        )

        binding_model = self.env["netvisor.invoice"]
        _logger.debug(f"Using XML string {xml_string}")

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        if binding and not backend.customer_invoice_allow_updating:
            _logger.info(
                _(
                    "Updating invoices is disabled. Not sending '{}'.".format(
                        record.name
                    )
                )
            )
            return _("Updating invoices to Netvisor is not allowed")

        if binding:
            # Update invoice
            endpoint = f"salesinvoice.nv?method=edit&id={binding.external_id}"
            backend._api_request_post(endpoint, xml_string)

            msg = _("Updated invoice '{}'".format(record.name))
        else:
            endpoint = "salesinvoice.nv?method=add"
            res = backend._api_request_post(endpoint, xml_string)
            if res:
                binding = binding_model.create(
                    {
                        "backend_id": backend.id,
                        "external_id": res.get("InsertedDataIdentifier"),
                        "odoo_id": record.id,
                    }
                )

                msg = _("Created invoice '{}'".format(record.display_name))
            else:
                raise MappingError(
                    _(
                        "Something went wrong when exporting invoice. "
                        "Please see log for more details"
                    )
                )

        # Save sent XML for debugging purposes
        xml_name = "%s_netvisor_salesinvoice.xml" % (record.name.replace("/", "_"))
        xml_string = "<?xml version='1.0' encoding='UTF-8'?>" + xml_string
        self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_string,
                "res_model": "account.move",
                "res_id": record.id,
                "mimetype": "application/xml",
            }
        )

        # Update Odoo invoice information
        job_desc = _("Import invoice details for {}".format(binding.odoo_id.name))
        binding.with_delay(description=job_desc).netvisor_import_invoice_details(
            binding.odoo_id
        )

        if binding.reversed_entry_id:
            # Match credit note to the original invoice
            job_desc = _(
                "Mark invoice {} as reversed".format(binding.reversed_entry_id.name)
            )

            binding.with_delay(description=job_desc).netvisor_match_credit_note()

        return msg

    def _validate(self, record):
        for line in record.invoice_line_ids:
            if line.display_type in ["line_section", "line_note"]:
                continue

            # Check if there are multiple taxes per line
            taxes = line.tax_ids
            if len(taxes) > 1:
                raise MappingError(
                    _(
                        "Please define only one tax for invoice line '{}'".format(
                            line.name
                        )
                    )
                )
            elif len(taxes) < 1:
                raise MappingError(
                    _("Please define one tax for invoice line '{}'".format(line.name))
                )

            tax = taxes[0]

            if tax.netvisor_code == "-":
                err = _(
                    "The tax '{}' is misconfigured. Please configure 'Netvisor VAT code' for that".format(
                        tax.name
                    )
                )
                raise ValidationError(err)

    def update_status(self, record):
        """Update invoice status to Netvisor"""
        netvisor_status = record.netvisor_status

        if record.payment_state in ["paid", "reversed"]:
            netvisor_status = "paid"
        elif record.is_move_sent:
            netvisor_status = "open"

        values = {}
        for binding in record.netvisor_bind_ids:
            endpoint = "updatesalesinvoicestatus.nv?netvisorkey={}&status={}".format(
                binding.external_id, netvisor_status
            )
            binding.backend_id._api_request_post(endpoint, values)

        record.netvisor_status = netvisor_status
        return f"Updated status to {netvisor_status}"

    def match_credit_note(self, binding):
        """Match credit note"""

        if binding.reversed_entry_id and binding.reversed_entry_id.netvisor_bind_ids:
            if len(binding.reversed_entry_id.netvisor_bind_ids) > 1:
                raise ValidationError(
                    _("Multiple bindings for one invoice is not supported.")
                )
            reversed_binding = binding.reversed_entry_id.netvisor_bind_ids[0]
            backend = binding.backend_id
            endpoint = "matchcreditnote.nv"

            xml_string = self.env["ir.qweb"]._render(
                "connector_netvisor.netvisor_matchcreditnote",
                {"invoice": binding, "reverse": reversed_binding},
            )

            res = backend._api_request_post(endpoint, xml_string)

        else:
            res = _("No refunded invoice to match")
        return res

    @mapping
    def invoicing_customer(self, record):
        res = {}

        # Export the partner to
        # a) Create a new partner
        # b) Update existing partner values
        record.partner_id.action_netvisor_export_record(
            use_queue=False, company_id=record.company_id.id
        )

        binding = record.partner_id.netvisor_bind_ids.filtered(
            lambda r: r.backend_id.company_id == record.company_id
        )

        if binding:
            # If partner identifier is known, use it
            res["invoicing_customer_identifier"] = binding.external_id
        else:
            # Partner seems to be mandatory?
            raise ValidationError(
                _(
                    "'{}' is not yet exported to Netvisor.".format(
                        record.partner_id.name
                    )
                )
            )
        return res

    @mapping
    def invoice_lines(self, record):
        """
        Return mapping for invoice lines
        :param record: Account move record
        :return:
        """
        invoice_lines = list()
        for line in record.invoice_line_ids:
            # Export the product to
            # a) Create a new product
            # b) Update existing product values
            line.product_id.action_netvisor_export_record(
                use_queue=False, company_id=record.company_id.id
            )

            product_identifier = line.product_id.netvisor_bind_ids.filtered(
                lambda r: r.backend_id.company_id == record.company_id
            )

            if len(product_identifier) != 1:
                raise MappingError(
                    _(
                        "Product '{}' is not found from Netvisor! "
                        "Please export products to Netvisor before sending the invoice".format(
                            line.product_id.display_name
                        )
                    )
                )

            invoice_lines.append(
                {
                    "dimension": self._get_dimensions(line),
                }
            )

        return {"invoice_lines": invoice_lines}
