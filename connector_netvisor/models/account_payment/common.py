import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.payment",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    netvisor_send = fields.Boolean(
        string="Send to Netvisor",
        help="Uncheck this to disable sending the payment to Netvisor",
        default=True,
    )

    def action_netvisor_export_record(self, use_queue=False, company_id=False):
        """
        Export payment(s) to Netvisor
        :return:
        """
        for record in self:
            if not record.netvisor_send:
                return _("'Send to Netvisor' is disabled. Payment was not sent")

            netvisor_model = self.env["netvisor.payment"]

            if not company_id and record.company_id:
                company_id = record.company_id.id

            if company_id:
                netvisor_model = netvisor_model.with_context(company_id=company_id)

            if use_queue:
                # Queued sending
                job_desc = _(
                    "Netvisor: export payment '{}' [Odoo ID: {}]".format(
                        record.display_name, record.id
                    )
                )
                netvisor_model.with_delay(description=job_desc).netvisor_export_payment(
                    record, company_id
                )
            else:
                # Immediate sending
                netvisor_model.netvisor_export_payment(record, company_id)
