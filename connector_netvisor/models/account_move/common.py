from odoo import fields
from odoo import models
from odoo import _


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

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_invoice(backend, record)

    def netvisor_update_status(self, record):
        """
        Update status from Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.update_status(backend, record)

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
                record.odoo_id.button_draft()
            elif invoice_status == "paid":
                record.payment_state = invoice_status

            record.netvisor_status = invoice_status


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

    def action_netvisor_export_invoice(self):
        """
        Export (send) invoice(s) to Netvisor
        :return:
        """
        netvisor_model = self.env["netvisor.invoice"]

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

    def action_netvisor_update_status(self):
        """
        Update status from Netvisor
        """
        netvisor_model = self.env["netvisor.invoice"]

        if len(self) == 1:
            netvisor_model.netvisor_update_status(self)
        else:
            for record in self:
                job_desc = _(
                    "Netvisor: update invoice status for '{}'".format(
                        record.display_name
                    )
                )
                netvisor_model.with_delay(description=job_desc).netvisor_update_status(
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
