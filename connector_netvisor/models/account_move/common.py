from odoo import api
from odoo import fields
from odoo import models
from odoo import _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.invoice",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    netvisor_status = fields.Selection(
        string="Netvisor status",
        selection=[
            ("open", "Open"),
            ("overdue", "Overdue"),
            ("paid", "Paid"),
            ("unsent", "Unsent"),
            ("creditloss", "Credit loss"),
            ("rejected", "Rejected"),
        ],
        copy=False,
        readonly=True,
    )

    netvisor_send = fields.Boolean(
        string="Send to netvisor",
        help="Uncheck this to skip sending the invoice to Netvisor on confirm",
        default=True,
    )

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        compute="_compute_attachment_ids",
    )

    def _compute_attachment_ids(self):
        ir_attachment = self.env["ir.attachment"]
        for record in self:
            attachment_ids = ir_attachment.search(
                [
                    ("res_id", "=", record.id),
                    ("res_model", "=", self._name),
                ]
            )

            record.attachment_ids = attachment_ids

    @api.model
    def _get_invoice_in_payment_state(self):
        # Mark the invoice as paid in Netvisor when it's marked as paid in Odoo
        res = super()._get_invoice_in_payment_state()

        if res == "paid":
            # Set Netvisor invoice as paid
            for record in self:
                if record.move_type in ["out_invoice", "out_refund"]:
                    for binding in record.netvisor_bind_ids:
                        job_desc = _("Mark invoice {} as paid".format(record.name))

                        binding.with_delay(description=job_desc).netvisor_export_status(
                            record
                        )

        return res

    def action_netvisor_export_invoice(self):
        """
        Export (send) invoice(s) to Netvisor
        :return:
        """
        netvisor_model = self.env["netvisor.invoice"].sudo()

        if len(self) == 1:
            # Only use direct send when validating one invoice
            # Otherwise we might end up with a situation where the first
            # invoice(s) are sent, but one of the following invoices end up
            # with API error and will rollback the whole action in Odoo,
            # even though some invoices were sent to Netvisor
            netvisor_model.netvisor_export_invoice(self)
        else:
            # Use delayed send to allow re-sending invoices with API errors
            for record in self:
                job_desc = _("Netvisor: send invoice '{}'".format(record.display_name))
                netvisor_model.with_delay(description=job_desc).netvisor_export_invoice(
                    record
                )

    def action_netvisor_import_status(self):
        """
        Update status from Netvisor
        """
        netvisor_model = self.env["netvisor.invoice"]

        if len(self) == 1:
            netvisor_model.netvisor_import_status(self)
        else:
            for record in self:
                job_desc = _(
                    "Netvisor: import invoice status for '{}'".format(
                        record.display_name
                    )
                )
                netvisor_model.with_delay(description=job_desc).netvisor_import_status(
                    record
                )

    def action_netvisor_export_status(self):
        """
        Update status to Netvisor
        """
        netvisor_model = self.env["netvisor.invoice"]

        if len(self) == 1:
            netvisor_model.netvisor_export_status(self)
        else:
            for record in self:
                job_desc = _(
                    "Netvisor: export invoice status for '{}'".format(
                        record.display_name
                    )
                )
                netvisor_model.with_delay(description=job_desc).netvisor_export_status(
                    record
                )

    def action_post(self):
        """
        Auto-send invoices to Netvisor when Validating
        """
        res = super().action_post()

        # Send invoice(s) to netvisor
        self.action_netvisor_export_invoice()

        return res
