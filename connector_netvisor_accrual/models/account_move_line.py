from odoo import api
from odoo import fields
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    accrual_rule_id = fields.Many2one(
        comodel_name="account.accrual.rule",
        string="Accrual rule",
    )

    @api.onchange("product_id")
    def onchange_product_id_set_accrual_rule(self):
        for record in self:
            if record.product_id:
                record.accrual_rule_id = (
                    record.product_id.product_tmpl_id.accrual_rule_id
                )
            else:
                record.accrual_rule_id = False

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if (
            "accrual_rule_id" not in vals
            and res.product_id
            and res.product_id.product_tmpl_id.accrual_rule_id
        ):
            res.accrual_rule_id = res.product_id.product_tmpl_id.accrual_rule_id

        return res
