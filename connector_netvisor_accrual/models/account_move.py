from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    accrual_rule_id = fields.Many2one(
        comodel_name="account.accrual.rule",
        string="Accrual rule",
    )

    # TODO: division_curve_name
