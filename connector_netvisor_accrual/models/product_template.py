from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    accrual_rule_id = fields.Many2one(
        comodel_name="account.accrual.rule",
        string="Accrual rule",
        help="Use accrual rule for invoice lines with this product",
    )
