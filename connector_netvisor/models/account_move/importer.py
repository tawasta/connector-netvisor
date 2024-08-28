import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class NetvisorInvoiceImportMapper(Component):
    _name = "netvisor.invoice.import.mapper"
    _description = "Netvisor Invoice Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.invoice"]

    def update_status(self, backend, record):
        """
        Update invoice status
        :param backend: Netvisor backend record
        :param netvisor_key: Netvisor external id
        :return:
        """

        binding = record.netvisor_bind_ids.filtered(
            lambda r: r.backend_id.company_id == record.company_id
        )

        if not binding:
            raise ValidationError(_("Please send the invoice to Netvisor first"))

        endpoint = f"getsalesinvoice.nv?netvisorkey={binding.external_id}"
        invoice = backend._api_request_get(endpoint)

        invoice_status = (
            invoice.get("InvoiceStatus").get("#text").lower().replace(" ", "")
        )

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

        endpoint = f"getsalesinvoice.nv?netvisorkey={binding.external_id}"
        invoice = backend._api_request_get(endpoint)
        invoice_status = (
            invoice.get("InvoiceStatus").get("#text").lower().replace(" ", "")
        )

        vals = {
            "name": invoice.get("SalesInvoiceNumber"),
            "payment_reference": invoice.get("SalesInvoiceReferencenumber"),
            "netvisor_status": invoice_status,
        }

        binding.write(vals)

        return _("Updated details for {}".format(binding.odoo_id))
