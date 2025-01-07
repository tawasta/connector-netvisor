import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class NetvisorInvoiceImportMapper(Component):
    _name = "netvisor.invoice.import.mapper"
    _description = "Netvisor Invoice Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.invoice"]

    def update_status(self, record):
        """
        Update invoice status
        :param netvisor_key: Netvisor external id
        :return:
        """

        binding = record.netvisor_bind_ids.filtered(
            lambda r: r.backend_id.company_id == record.company_id
        )

        if not binding:
            raise ValidationError(_("Please send the invoice to Netvisor first"))

        if record.is_sale_document():
            endpoint = f"getsalesinvoice.nv?netvisorkey={binding.external_id}"
        elif record.is_purchase_document():
            endpoint = f"getpurchaseinvoice.nv?netvisorkey={binding.external_id}"

        invoice = binding.backend_id._api_request_get(endpoint)

        if not invoice:
            return _("Invoice not found from Netvisor")

        invoice_status = invoice.get("InvoiceStatus")
        if isinstance(invoice_status, dict):
            # Sales invoice returns a dict
            invoice_status = invoice_status.get("#text")

        invoice_status = invoice_status.lower().replace(" ", "")

        if record.netvisor_status != invoice_status:
            res = _(
                "Updated status from '{}' to '{}'".format(
                    record.netvisor_status, invoice_status
                )
            )
            binding.action_update_invoice_status(invoice_status)

        else:
            res = _("Status '{}' is up to date. Nothing to do".format(invoice_status))

        return res

    def update_details(self, backend, record):
        """
        Update invoice details
        :param backend: Netvisor backend record
        :param record: Odoo record
        :return:
        """
        binding = record.netvisor_bind_ids.filtered(
            lambda r: r.backend_id.company_id == record.company_id
        )

        if not binding:
            raise ValidationError(_("Please send the invoice to Netvisor first"))

        if record.is_sale_document():
            endpoint = f"getsalesinvoice.nv?netvisorkey={binding.external_id}"
        elif record.is_purchase_document():
            endpoint = f"getpurchaseinvoice.nv?netvisorkey={binding.external_id}"

        invoice = backend._api_request_get(endpoint)
        invoice_status = invoice.get("InvoiceStatus")
        if isinstance(invoice_status, dict):
            # Sales invoice returns a dict
            invoice_status = invoice_status.get("#text")

        vals = {
            "name": invoice.get("SalesInvoiceNumber")
            or invoice.get("PurchaseInvoiceNumber"),
            "payment_reference": invoice.get("SalesInvoiceReferencenumber")
            or invoice.get("PurchaseInvoiceReferencenumber"),
            "netvisor_status": invoice_status.lower().replace(" ", ""),
        }

        binding.write(vals)

        return _("Updated details for {}".format(binding.odoo_id))

    def import_purchase_invoice(self, backend, netvisor_key):
        """
        Import or update a purchase invoice from Netvisor.
        :param backend: Netvisor backend record
        :param record: Purchase invoice record
        :return:
        """
        netvisor_model = self.env["netvisor.invoice"]

        endpoint = f"getpurchaseinvoice.nv?netvisorkey={netvisor_key}"
        invoice = backend._api_request_get(endpoint)
        attachments = invoice.get("Attachments", {}).get("Attachment", {})
        values = self.map_record(invoice).values()
        values["company_id"] = backend.company_id.id
        netvisor_key = invoice.get("PurchaseInvoiceNetvisorKey")

        # Search for existing binding
        existing_binding = netvisor_model.search(
            [
                ("external_id", "=", netvisor_key),
                ("backend_id", "=", backend.id),
            ],
            limit=1,
        )

        if existing_binding:
            # Updating purchase invoices is not implemented
            return _("Purchase invoice already imported. Nothing to do")

        # Create invoice
        account_move = self.env["account.move"]
        invoice_line_ids = values.pop("invoice_line_ids")
        invoice = account_move.create(values)
        invoice.write({"invoice_line_ids": invoice_line_ids})

        # Import attachments
        for attachment in attachments:
            _logger.debug(attachment)
            values = dict(
                datas=attachment.get("AttachmentBase64Data"),
                name=attachment.get("FileName", "n/a"),
                store_fname=attachment.get("FileName", "n/a"),
                type="binary",
                res_model="account.move",
                res_id=invoice.id,
                mimetype=attachment.get("ContentType", "Unknown"),
                description=attachment.get("Comment"),
            )

            _logger.debug("Creating attachment with values %s" % values)
            self.env["ir.attachment"].create(values)

        # No existing binding
        binding_values = {
            "backend_id": backend.id,
            "external_id": netvisor_key,
            "odoo_id": invoice.id,
        }

        netvisor_model.create(binding_values)

        return _("Created invoice '{}'".format(invoice.id))

    # Netvisor, Odoo
    direct = [
        ("PurchaseInvoiceNumber", "name"),
        ("PurchaseInvoiceReferencenumber", "payment_reference"),
        ("PurchaseInvoiceOurReference", "ref"),
        # TODO: PurchaseInvoiceYourReference
        # TODO: PurchaseInvoiceAgreementIdentifier
        ("PurchaseInvoiceDescription", "narration"),
    ]

    @mapping
    def invoice_date(self, record):
        value_date = record.get("PurchaseInvoiceValueDate").get("#text")
        invoice_date = record.get("PurchaseInvoiceDate").get("#text")

        res = {
            # Value date isn't always set
            "date": value_date or invoice_date,
            "invoice_date": invoice_date,
        }

        return res

    @mapping
    def invoice_date_due(self, record):
        date = record.get("PurchaseInvoiceDueDate").get("#text")

        res = {"invoice_date_due": date}

        return res

    @mapping
    def partner_id(self, record):
        code = record.get("VendorCode")
        name = record.get("VendorName")

        res_partner = self.env["res.partner"]

        company_registry = record.get("VendorOrganizationIdentifier")

        # Try to find partner by company registry, ref, or exact name
        partner_id = res_partner.search(
            [
                "|",
                "|",
                ("company_registry", "=", company_registry),
                ("ref", "=", code),
                ("name", "=", name),
            ]
        )

        if len(partner_id) != 1:
            # Only use an exact match, otherwise create a new partner
            partner_id = res_partner.create(
                {
                    "name": name,
                    "company_registry": company_registry,
                    "ref": code,
                    "street": record.get("VendorAddressline"),
                    "zip": record.get("VendorPostnumber"),
                    "city": record.get("VendorTown"),
                    # TODO VendorCountry
                }
            )

        res = {"partner_id": partner_id.id}
        return res

    @mapping
    def move_type(self, record):
        if record.get("InvoiceNetvisorKey"):
            # Sale invoice
            move_type = "out_invoice"
        elif record.get("PurchaseInvoiceNetvisorKey"):
            # Purchase invoice
            move_type = "in_invoice"

        return {"move_type": move_type}

    @mapping
    def invoice_line_ids(self, record):
        invoice_line_ids = list()

        invoice_lines_list = record.get("InvoiceLines")

        move_type = self.move_type(record).get("move_type", False)
        if invoice_lines_list.get("InvoiceLine"):
            # Sale invoice
            invoice_lines = invoice_lines_list.get("InvoiceLine")
        elif invoice_lines_list.get("PurchaseInvoiceLine"):
            # Purchase invoice
            invoice_lines = invoice_lines_list.get("PurchaseInvoiceLine")

        if isinstance(invoice_lines, dict):
            # Always put lines in a list
            invoice_lines = [invoice_lines]

        for line in invoice_lines:
            invoice_line_ids.append(
                (0, False, self.get_invoice_line(record, line, move_type))
            )

        res = {"invoice_line_ids": invoice_line_ids}

        return res

    # noinspection PyPep8Naming
    def get_invoice_line(self, record, line, move_type):
        # TODO: an option to auto-create new products by code or name
        # TODO: break this method into smaller methods

        price_unit = line.get("UnitPrice", 0)
        product_name = line.get("ProductName", "")
        product_code = line.get("ProductCode", "")
        vat_percent = line.get("VatPercent", 0)

        if isinstance(price_unit, str):
            price_unit = float(price_unit.replace(",", "."))

        if isinstance(vat_percent, str):
            vat_percent = float(vat_percent.replace(",", "."))

        if vat_percent:
            # Price unit is returned as a gross price
            price_unit = price_unit / (1 + vat_percent / 100)

        # In Odoo the invoice type dictates the sign, not the sign on the qty
        qty_factor = -1 if "refund" in move_type else 1

        # TODO: Should there be some logic between ordered amount and delivered amount?
        quantity = line.get("DeliveredAmount") or line.get("OrderedAmount") or 0

        if isinstance(quantity, str):
            quantity = float(quantity.replace(",", "."))

        line_values = {
            "netvisor_key": line.get("NetvisorKey"),
            "name": line.get("Description", ""),
            "discount": line.get("DiscountPercentage", 0),
            "price_unit": price_unit,
            "purchase_price": line.get("PurchasePrice", 0),
            "quantity": quantity * qty_factor,
        }

        if vat_percent:
            AccountTax = self.env["account.tax"]

            tax_scope = "purchase" if move_type == "in_invoice" else "sale"

            tax_vals = {
                "amount": vat_percent,
                "type_tax_use": tax_scope,
                "price_include": False,
            }
            tax = AccountTax.search([(k, "=", v) for k, v in tax_vals.items()], limit=1)

            if not tax:
                # Tax not found in Odoo, create one
                tax_vals["name"] = "{} %".format(vat_percent)
                tax = AccountTax.create(tax_vals)

            line_values["tax_ids"] = [(4, tax.id)]

        if line.get("Unit", False):
            uom = self.env["uom.uom"]
            unit = uom.search([("name", "=ilike", line.get("Unit"))], limit=1)

            if unit:
                line_values["product_uom_id"] = unit.id

        product_id = self.env["product.product"].search(
            [
                "|",
                ("name", "=", product_name),
                ("default_code", "=", product_code),
            ]
        )

        if len(product_id) == 1:
            line_values["product_id"] = product_id.id
        else:
            if product_code:
                line_values["name"] = "[{}] {}".format(product_code, product_name)
            else:
                line_values["name"] = product_name

        return line_values
