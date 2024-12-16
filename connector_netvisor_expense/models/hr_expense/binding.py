from odoo import _, fields, models


class NetvisorExpense(models.Model):
    """Binding Model for the Netvisor Expense"""

    _name = "netvisor.expense"
    _inherit = "netvisor.binding"
    _inherits = {"hr.expense": "odoo_id"}
    _description = "Netvisor Expense"

    odoo_id = fields.Many2one(
        comodel_name="hr.expense",
        string="Odoo Expense",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A Netvisor binding for this record already exists.",
        ),
    ]

    def netvisor_export_expense(self, record, company=False):
        """
        Export an expense to Netvisor
        :param record: Expense record
        :param company: Company ID
        :return:
        """
        backend = self.get_netvisor_backend(company)

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_expense(backend, record)
