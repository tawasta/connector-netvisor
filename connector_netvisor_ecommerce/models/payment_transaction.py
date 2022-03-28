from odoo import models


class PaymentTransaction(models.Model):

    _inherit = "payment.transaction"

    def _invoice_sale_orders(self):
        res = super(PaymentTransaction, self)._invoice_sale_orders()

        if self.env["ir.config_parameter"].sudo().get_param("sale.automatic_invoice"):
            for trans in self.filtered(lambda t: t.sale_order_ids):
                trans.invoice_ids.write(
                    {
                        "netvisor_delayed_send": True,
                    }
                )

        return res
