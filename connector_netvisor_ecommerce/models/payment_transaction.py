from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _invoice_sale_orders(self):
        res = super()._invoice_sale_orders()

        if self.env["ir.config_parameter"].sudo().get_param("sale.automatic_invoice"):
            for trans in self.filtered(lambda t: t.sale_order_ids):
                trans.invoice_ids.write(
                    {
                        "netvisor_delayed_send": True,
                    }
                )

        return res

    def _create_payment(self, **extra_create_values):
        res = super()._create_payment(**extra_create_values)
        self.invoice_ids.action_netvisor_export_status()

        return res
