from odoo import fields, models
from dateutil.relativedelta import relativedelta


class AccrualRule(models.Model):
    _name = "account.accrual.rule"
    _description = "Accrual rule for invoices"

    name = fields.Char()
    active = fields.Boolean(default=True)

    period_length = fields.Integer(
        string="Period (months)",
        help="How many months in the accrual period",
    )

    def get_accrual_start_month(self, start_date):
        self.ensure_one()
        res = start_date.month

        return res

    def get_accrual_start_year(self, start_date):
        self.ensure_one()
        res = start_date.year

        return res

    def get_accrual_end_month(self, start_date):
        self.ensure_one()
        res = (start_date + relativedelta(months=self.period_length)).month

        return res

    def get_accrual_end_year(self, start_date):
        self.ensure_one()
        res = (start_date + relativedelta(months=self.period_length)).year

        return res
