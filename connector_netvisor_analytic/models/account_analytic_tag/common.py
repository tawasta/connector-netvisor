from odoo import fields
from odoo import models


class NetvisorDimensionItem(models.Model):
    """Binding Model for the Netvisor Dimension Item"""

    _name = "netvisor.dimension.item"
    _inherit = "netvisor.binding"
    _inherits = {"account.analytic.tag": "odoo_id"}
    _description = "Netvisor Dimension Item"

    odoo_id = fields.Many2one(
        comodel_name="account.analytic.tag",
        string="Analytic tag",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A Netvisor binding for this analytic tag already exists.",
        ),
    ]

    def netvisor_import_dimension_item(self, dimension_item):
        """
        Import a dimension item from dict (originating from Netvisor)
        :param dimension_item: dict with dimension information
        :return:
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_dimension(backend, dimension_item)


class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.dimension.item",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )
