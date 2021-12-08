import datetime
from odoo import fields
from odoo import models
from odoo import _
import logging

_logger = logging.getLogger(__name__)


class NetvisorInvoice(models.Model):
    """Binding Model for the Netvisor Invoice"""

    _name = "netvisor.invoice"
    _inherit = "netvisor.binding"
    _inherits = {"account.move": "odoo_id"}
    _description = "Netvisor Invoice"

    odoo_id = fields.Many2one(
        comodel_name="account.move",
        string="Account move",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A Netvisor binding for this invoice already exists.",
        ),
    ]

    def netvisor_export_invoice(self, record):
        """
        Export an invoice to Netvisor
        """
        backend = self.get_netvisor_backend()
        _logger.debug(f"Exporting invoice {record.id} to Netvisor")

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_invoice(backend, record)

    def netvisor_import_status(self, record):
        """
        Update status from Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.update_status(backend, record)

    def netvisor_export_status(self, record):
        """
        Update status to Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.update_status(backend, record)

    def action_update_invoice_status(self, invoice_status):
        """
        Update invoice status in Odoo
        :param invoice_status: The invoice status to update to
        :return:
        """
        for record in self:
            if record.netvisor_status == invoice_status:
                # Nothing to do
                return
            elif invoice_status == "unsent":
                # Set to draft
                # Generally we don't want to do this
                # record.odoo_id.button_draft()
                pass
            elif invoice_status == "paid":
                # Set invoice as fully paid
                # TODO: get correct payment date
                # TODO: get correct payment method
                # TODO: get correct journal

                # This will currently fetch the first appicable method
                payment_method = self.env["account.payment.method"].search(
                    [("payment_type", "=", "inbound")], limit=1
                )

                payment_amount = record.amount_residual

                # This will currently set today as payment date
                # It is usually incorrect, but we don't have the correct data from Procountor here
                payment_date = datetime.date.today()

                payment_values = {
                    "amount": payment_amount,
                    "group_payment": True,
                    "payment_difference_handling": "open",
                    "currency_id": record.currency_id.id,
                    "payment_method_id": payment_method.id,
                    "payment_date": payment_date,
                }

                _logger.debug(_(f"Payment values: {payment_values}"))
                _logger.debug(_(f"Invoices to pay: {record.odoo_id.ids}"))

                self.env["account.payment.register"].with_context(
                    active_model="account.move", active_ids=record.odoo_id.ids
                ).create(payment_values)._create_payments()

            record.netvisor_status = invoice_status
