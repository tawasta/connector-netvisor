from odoo import _
from odoo.exceptions import ValidationError
from odoo.addons.connector.exception import MappingError
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from netvisor_api_client.exc import InvalidData
from odoo.addons.queue_job.exception import RetryableJobError
import logging

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
        if not record.netvisor_send:
            return _("Netvisor sending is disabled for this invoice")

        if record.reversed_entry_id and backend.auto_open_refunds:
            # Mark the to-be-created refund as open immediately
            record.netvisor_status = "open"

        values = self.map_record(record).values()

        values["print_channel_format"] = {
            "identifier": backend.print_channel_format,
            "type": backend.print_channel_format_type,
        }

        client = backend.authenticate()
        binding_model = self.env["netvisor.invoice"]
        _logger.debug(f"Using values {values}")

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        if binding and not backend.customer_invoice_allow_updating:
            _logger.info(
                _(f"Updating invoices is disabled. Not sending '{record.name}'.")
            )
            return _("Updating invoices to Netvisor is not allowed")

        try:
            if binding:
                # Update invoice
                client.sales_invoices.update(binding.external_id, values)
                msg = _(f"Updated invoice '{record.name}'")
            else:
                res = client.sales_invoices.create(values)
                if res:
                    binding = binding_model.create(
                        {
                            "backend_id": backend.id,
                            "external_id": res,
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
        except InvalidData as e:
            raise ValidationError(e)

        # Update Odoo invoice information
        netvisor_invoice = client.sales_invoices.get(binding.external_id)
        invoice_status = netvisor_invoice.get("invoice_status").lower().replace(" ", "")

        if binding.reversed_entry_id:
            # Match credit note to the original invoice
            job_desc = _(
                "Mark invoice {} as reversed".format(binding.reversed_entry_id.name)
            )

            binding.with_delay(description=job_desc).netvisor_match_credit_note()

        binding.odoo_id.write(
            {
                "name": netvisor_invoice.get("number"),
                "payment_reference": netvisor_invoice.get("reference_number"),
                "netvisor_status": invoice_status,
            }
        )

        return msg

    def update_status(self, backend, record):
        """ Update invoice status to Netvisor """
        client = backend.authenticate()
        binding_model = self.env["netvisor.invoice"]
        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )
        netvisor_status = record.netvisor_status

        if record.payment_state in ["paid", "reversed"]:
            netvisor_status = "paid"

        res = client.sales_invoices.update_status(binding.external_id, netvisor_status)
        record.netvisor_status = netvisor_status
        return res

    def match_credit_note(self, binding):
        """ Match credit ntoe """
        client = binding.backend_id.authenticate()
        if binding.reversed_entry_id and binding.reversed_entry_id.netvisor_bind_ids:
            if len(binding.reversed_entry_id.netvisor_bind_ids) > 1:
                raise ValidationError(
                    _("Multiple bindings for one invoice is not supported.")
                )
            reversed_binding = binding.reversed_entry_id.netvisor_bind_ids[0]

            try:
                res = client.sales_invoices.match_credit_note(
                    {
                        "credit_note_netvisor_key": binding.external_id,
                        "invoice_netvisor_key": reversed_binding.external_id,
                    }
                )
            except InvalidData:
                raise RetryableJobError(
                    _("Refund invoice not found. It may not be sent in Netvisor yet")
                )

        else:
            res = _("No refunded invoice to match")
        return res

    # Odoo, Netvisor
    direct = [
        ("invoice_date", "date"),
        ("date", "event_date"),
        ("amount_total_signed", "amount"),
    ]

    @mapping
    def currency(self, record):
        return {"currency": record.currency_id.name}

    @mapping
    def status(self, record):
        netvisor_status = record.netvisor_status or "unsent"

        if record.state == "draft":
            netvisor_status = "unsent"
        elif record.state == "cancel":
            netvisor_status = "rejected"

        return {"status": netvisor_status}

    @mapping
    def invoicing_customer(self, record):
        res = {}

        binding = record.partner_id.netvisor_bind_ids.filtered(
            lambda r: r.backend_id.company_id == record.company_id
        )

        if binding:
            # If partner identifier is known, use it
            res["invoicing_customer_identifier"] = binding.external_id
        else:
            # Partner seems to be mandatory?
            raise ValidationError(
                _(f"'{record.partner_id.name}' is not yet exported to Netvisor.")
            )
            # If partner identifier is not known, send all information
            res["invoicing_customer_name"] = record.partner_id.display_name
            res["invoicing_customer_address_line"] = record.partner_id.street or ""
            res["invoicing_customer_additional_address_line"] = (
                record.partner_id.street2 or ""
            )
            res["invoicing_customer_post_number"] = record.partner_id.zip or ""
            res["invoicing_customer_town"] = record.partner_id.city or ""

            # TODO: add type to netvisor-api-client
            # res["invoicing_customer_country_code"] = record.partner_id.country_id.code
        return res

    @mapping
    def delivery_address_name(self, record):
        return {"delivery_address_name": record.partner_shipping_id.display_name}

    @mapping
    def delivery_address_line(self, record):
        return {
            "delivery_address_line": record.partner_shipping_id.get_combined_street()
        }

    @mapping
    def delivery_address_post_number(self, record):
        return {"delivery_address_post_number": record.partner_shipping_id.zip or ""}

    @mapping
    def delivery_address_town(self, record):
        return {"delivery_address_town": record.partner_shipping_id.city or ""}

    @mapping
    def delivery_address_country_code(self, record):
        # TODO: add type to netvisor-api-client
        return
        return {
            "delivery_address_country_code": record.partner_shipping_id.country_id.code
            or ""
        }

    @mapping
    def payment_term_net_days(self, record):
        net_days = record.invoice_date_due - record.invoice_date

        return {"payment_term_net_days": net_days.days}

    @mapping
    def free_text_before_lines(self, record):
        res = {}

        if record.move_type == "out_refund":
            # Ref will contain the information about refunded invoice
            res["free_text_before_lines"] = record.ref

        return res

    @mapping
    def free_text_after_lines(self, record):
        res = {"free_text_after_lines": record.narration or ""}

        return res

    @mapping
    def our_reference(self, record):
        return {"our_reference": ""}

    @mapping
    def your_reference(self, record):
        res = {}

        if record.move_type != "out_refund":
            # In refunds the ref goes to "free_text_before_lines"
            res["your_reference"] = record.ref or ""

        return res

    @mapping
    def private_comment(self, record):
        return {"private_comment": ""}

    @mapping
    def override_rate_of_overdue(self, record):
        # TODO: add overdue interest when netvisor-api-client supports it
        return
        if hasattr(record, "overdue_interest"):
            return {"override_rate_of_overdue": 8}

    @mapping
    def invoice_lines(self, record):
        """
        Return mapping for invoice lines
        :param record: Account move record
        :return:
        """
        invoice_lines = list()
        for line in record.invoice_line_ids:
            taxes = line.tax_ids
            if len(taxes) != 1:
                raise MappingError(_("Please define one tax for each invoice line"))
            tax = taxes[0]

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

            quantity = line.quantity
            if record.move_type == "out_refund":
                # Negative quantity for refunds
                quantity *= -1

            if tax.netvisor_code == "-":
                raise ValidationError(
                    _(
                        f"The tax '{tax.name}' is misconfigured. Please configure 'Netvisor VAT code' for that"
                    )
                )

            invoice_lines.append(
                {
                    "identifier": {
                        "identifier": product_identifier.external_id,
                        "type": "netvisor",
                    },
                    "name": line.product_id.name,
                    "free_text": line.name,
                    "unit_price": {"amount": line.price_unit, "type": "net"},
                    "vat_percentage": {
                        "percentage": tax.amount,
                        "code": tax.netvisor_code,
                    },
                    "quantity": quantity,
                    "discount_percentage": line.discount,
                    "dimension": self._get_dimensions(line),
                    "accounting_account_suggestion": line.account_id.code,
                }
            )

        return {"invoice_lines": invoice_lines}

    @mapping
    def attachments(self, record):
        """
        Return list of attachments
        :param record: Account move record
        :return:
        """
        attachments = list()
        for attachment in record.attachment_ids:
            # Netvisor API won't receive the same attachment twice,
            # so we don't need to check if the attachment is already sent
            attachments.append(
                {
                    "mime_type": attachment.mimetype,
                    "description": attachment.description,
                    "filename": attachment.name,
                    "data": attachment.datas,
                    "type": "pdf",
                }
            )

        return {"attachments": attachments}

    def _get_dimensions(self, record):
        """
        A overridable function for adding dimensions to invoice line
        :param record: Account move line
        :return: dict with dimension and dimension item
        """
        return []
