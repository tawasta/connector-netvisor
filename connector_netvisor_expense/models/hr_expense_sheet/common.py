from odoo import _, fields, models


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
            msg = _("Expense report posted to Netvisor")
            record.message_post(body=msg)
            record.set_to_paid()
            # Force payment state
            record.payment_state = "paid"

            # Force expense line state
            record.expense_line_ids.write({"state": "done"})

    def _do_create_moves(self):
        # Don't create moves when using Netvisor expenses.
        # Netvisor will handle the payment
        self.set_to_paid()
        # Force payment state
        self.payment_state = "paid"

        # Return empty recordset
        moves = self.env["account.move"]
        return moves

    def _do_reverse_moves(self):
        # Don't create reverse moves when using Netvisor expenses
        return

    def _prepare_bills_vals(self):
        res = super()._prepare_bills_vals()

        # Don't send bills to Netvisor
        res["netvisor_send"] = False

        return res
