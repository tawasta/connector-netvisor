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

        netvisor_key = binding.external_id
        client = backend.authenticate()
        invoice = client.sales_invoices.get(netvisor_key)
        invoice_status = invoice.get("invoice_status").lower().replace(" ", "")

        if record.netvisor_status != invoice_status:
            res = _(
                f"Updated status from '{record.netvisor_status}' to '{invoice_status}'"
            )
            binding.action_update_invoice_status(invoice_status)

        else:
            res = _(f"Status '{invoice_status}' is up to date. Nothing to do")

        return res
