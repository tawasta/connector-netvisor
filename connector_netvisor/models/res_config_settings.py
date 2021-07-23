from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_connector_netvisor_analytic = fields.Boolean(
        "Netvisor dimensions",
        help="Use dimensions (analytic tags) with Netvisor integration. "
        "This will install connector_netvisor_analytic",
    )
