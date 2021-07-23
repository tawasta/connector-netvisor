from odoo import fields
from odoo import models
from odoo import _


class NetvisorDimension(models.Model):
    """Binding Model for the Netvisor Dimension"""

    _name = "netvisor.dimension"
    _inherit = "netvisor.binding"
    _inherits = {"account.analytic.dimension": "odoo_id"}
    _description = "Netvisor Dimension"

    odoo_id = fields.Many2one(
        comodel_name="account.analytic.dimension",
        string="Analytic dimension",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A Netvisor binding for this dimension already exists.",
        ),
    ]

    def netvisor_import_dimensions(self):
        """
        Import all dimensions from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend()
        client = backend.authenticate()
        records = client.dimensions.list()

        for record in records:
            job_desc = _("Netvisor: import dimension '{}'".format(record.get("name")))
            self.with_delay(description=job_desc).netvisor_import_dimension(record)

    def netvisor_import_dimension(self, dimension):
        """
        Import a dimension from Netvisor
        :param dimension: dict with dimension information
        :return:
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_dimension(backend, dimension)


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.dimension",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )
