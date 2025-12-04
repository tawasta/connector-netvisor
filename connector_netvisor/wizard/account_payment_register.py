from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    netvisor_send = fields.Boolean(
        string="Send to Netvisor",
        help="Uncheck this to disable sending the payment to Netvisor",
        default=True,
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super()._create_payment_vals_from_wizard(batch_result)

        res["netvisor_send"] = self.netvisor_send

        return res
