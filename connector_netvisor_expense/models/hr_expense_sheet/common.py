from odoo import fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    expenses_sent_to_netvisor = fields.Boolean(
        "Expenses sent to Netvisor",
        default=False,
        readonly=True,
    )

    def action_netvisor_export_expenses(self):
        for record in self:
            record.expense_line_ids.action_netvisor_export_record()
            record.expenses_sent_to_netvisor = True
