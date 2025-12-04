import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext

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
            ("requested", "Requested"),
            ("reminded", "Reminded"),
            ("dueforpayment", "Due for payment"),
            ("collected", "Collected"),
        ],
        copy=False,
        readonly=True,
    )

    netvisor_send = fields.Boolean(
        string="Send to netvisor",
        help="Uncheck this to skip sending the invoice to Netvisor on confirm",
        default=True,
    )

    netvisor_sent = fields.Datetime(
        string="Sent to Netvisor", readonly=True, copy=False
    )

    netvisor_delayed_send = fields.Boolean(
        string="Netvisor delayed send",
        default=False,
        copy=False,
        help="When sending invoice to Netvisor, send it as a delayed job. "
        "This is preferred when sending invoices programmatically or in a batch",
    )

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        compute="_compute_attachment_ids",
    )

    narration_plaintext = fields.Char(
        string="Narration plaintext",
        compute="_compute_narration_plaintext",
        help="Helper field for narration",
    )

    @api.depends("posted_before", "state", "journal_id", "date")
    def _compute_name(self):
        for record in self:
            if record.is_sale_document and record.amount_total_signed == 0:
                # Don't set invoice numbers for zero sum invoices.
                # They can't be sent to Netvisor and this would mess up the sequencing
                record.name = "/"
            else:
                super(AccountMove, record)._compute_name()

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

    def _compute_narration_plaintext(self):
        for record in self:
            if record.narration:
                record.narration_plaintext = html2plaintext(record.narration)
            else:
                record.narration_plaintext = ""

    @api.depends("date", "auto_post")
    def _compute_hide_post_button(self):
        super()._compute_hide_post_button()
        for record in self.filtered("netvisor_send"):
            record.hide_post_button = record.netvisor_send

    def _compute_show_reset_to_draft_button(self):
        # Disallow resetting invoice to draft if Netvisor binding exists
        res = super()._compute_show_reset_to_draft_button()

        for record in self:
            if record.netvisor_bind_ids:
                record.show_reset_to_draft_button = False

        return res

    def write(self, vals):
        res = super().write(vals)

        if vals.get("is_move_sent"):
            # If invoice is set as sent, export the status to Netvisor
            for record in self:
                if (
                    record.transmit_method_id.code == "mail"
                    and record.netvisor_status == "unsent"
                ):
                    # When invoice is set as sent
                    job_desc = _(f"Set invoice '{record.name}' as sent in Netvisor")
                    record.with_delay(
                        description=job_desc
                    ).action_netvisor_export_status()

        if vals.get("payment_id"):
            for record in self.filtered(lambda r: r.is_entry()):
                # Send the payment to Netvisor
                record.payment_id.action_netvisor_export_record(use_queue=True)

        return res

    def action_netvisor_export_invoice(self):
        """
        Export (send) invoice(s) to Netvisor
        :return:
        """
        for record in self:
            if not record.partner_id.netvisor_bind_ids and not record.partner_id.ref:
                msg = _(
                    "Partner '%s' is missing a partner reference. Please add one",
                    record.partner_id.name,
                )
                raise ValidationError(msg)

        if len(self) == 1 and not self.netvisor_delayed_send:
            # Only use direct send when validating one invoice
            # Otherwise we might end up with a situation where the first
            # invoice(s) are sent, but one of the following invoices end up
            # with API error and will roll back the whole action in Odoo,
            # even though some invoices were sent to Netvisor
            netvisor_model = self.env["netvisor.invoice"].sudo()
            netvisor_model.netvisor_export_invoice(self)
        else:
            # Use delayed send to allow re-sending invoices with API errors
            for record in self:
                netvisor_model = self.env["netvisor.invoice"].sudo()
                if record.company_id:
                    netvisor_model = netvisor_model.with_context(
                        company_id=record.company_id.id
                    )

                job_desc = _(
                    f"Netvisor: send invoice {record.name} [Odoo ID: {record.id}]"
                )
                netvisor_model.with_delay(description=job_desc).netvisor_export_invoice(
                    record
                )

    def action_netvisor_import_invoice(self):
        """
        Update invoice information from Netvisor
        """
        for record in self:
            for binding in record.netvisor_bind_ids:
                binding.netvisor_import_purchase_invoice(
                    binding.external_id, update=True
                )

    def action_netvisor_import_status(self):
        """
        Update status from Netvisor
        """
        netvisor_model = self.env["netvisor.invoice"]

        if len(self) == 1 and not self.netvisor_delayed_send:
            netvisor_model.netvisor_import_status(self)
        else:
            for record in self:
                job_desc = _(
                    f"Netvisor: import invoice status for '{record.display_name}'"
                )
                netvisor_model.with_delay(description=job_desc).netvisor_import_status(
                    record
                )

    def action_netvisor_export_status(self):
        """
        Update status to Netvisor
        """
        netvisor_model = self.env["netvisor.invoice"]

        if len(self) == 1 and not self.netvisor_delayed_send:
            netvisor_model.netvisor_export_status(self)
        else:
            for record in self:
                job_desc = _(
                    f"Netvisor: export invoice status for '{record.display_name}'"
                )
                netvisor_model.with_delay(description=job_desc).netvisor_export_status(
                    record
                )

    def action_netvisor_unlink(self):
        """Unlink the Netvisor invoice"""
        for record in self:
            record.netvisor_sent = False

            for binding in self.netvisor_bind_ids:
                msg = _(
                    "Removed Netvisor invoice binding for Netvisor id '%s'",
                    binding.external_id,
                )
                record.message_post(body=msg)
                binding.sudo().unlink()

    def action_reset_netvisor_sent(self):
        """
        Reset "netvisor_sent"-state, to allow resending
        """
        self.write({"netvisor_sent": False})

    def _post(self, soft=True):
        """
        Auto-send invoices to Netvisor when Validating
        """
        res = super()._post(soft)

        # Omit all moves that are not sale or purchase invoices
        # Also sort the invoices so the numbering will stay in order
        # (Netvisor should give the same number)
        sale_invoices = self.filtered(lambda r: r.is_sale_document()).sorted("name")
        purchase_invoices = self.filtered(lambda r: r.is_purchase_document()).sorted(
            "name"
        )

        # Set temporary prefix for invoice to avoid confusion and conflicts,
        #  if Odoo is not in sync with Netvisor sequence
        #  E.g. invoices have been created in Netvisor
        for sales_invoice in sale_invoices:
            if sales_invoice.name[0:3] != "INV":
                new_name = f"INV/{sales_invoice.name}"
                i = 1
                while self.search([("name", "=", new_name)]):
                    # If there is an overlapping name, add a sequence number
                    new_name = new_name + f"_{i}"
                    i += 1

                sales_invoice.name = new_name

        # Send sale invoice(s) to Netvisor
        sale_invoices.action_netvisor_export_invoice()

        # Send purchase invoice(s) to Netvisor
        purchase_invoices.action_netvisor_export_invoice()

        return res

    def button_draft(self):
        """
        Disable resetting to draft if Netvisor binding exists
        """
        for record in self:
            if record.netvisor_bind_ids:
                msg = _(
                    "Cannot reset to draft, invoice is already sent to Netvisor. "
                    "Please use 'Unlink Netvisor invoice' first."
                )
                raise ValidationError(msg)
            else:
                record.netvisor_sent = False

        return super().button_draft()
