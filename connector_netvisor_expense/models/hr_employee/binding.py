from odoo import _, fields, models


class NetvisorEmployee(models.Model):
    """Binding Model for the Netvisor Employee"""

    _name = "netvisor.employee"
    _inherit = "netvisor.binding"
    _inherits = {"hr.employee": "odoo_id"}
    _description = "Netvisor Employee"

    odoo_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Odoo Employee",
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

    def netvisor_export_employee(self, record, company=False):
        """
        Export an employee to Netvisor
        :param record: Employee record
        :param company: Company ID
        :return:
        """
        backend = self.get_netvisor_backend(company)

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_employee(backend, record)

    def netvisor_import_employee(self, netvisor_key):
        """
        Import an employee from Netvisor
        :param netvisor_key: Employee key in Netvisor
        :return:
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_employee(backend, netvisor_key)
