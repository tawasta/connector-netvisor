import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class NetvisorBackend(models.Model):

    _inherit = "netvisor.backend"

    def action_import_dimensions(self):
        """
        Import dimensions from Netvisor
        :return:
        """
        _logger.debug(_("Importing dimensions from Netvisor"))
        netvisor_model = self.env["netvisor.dimension"]

        for record in self:
            job_desc = _(
                "Netvisor: import dimensions for {}".format(record.company_id.name)
            )

            netvisor_model.with_delay(description=job_desc).netvisor_import_dimensions()
