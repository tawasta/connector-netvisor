import logging
from odoo import models
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NetvisorBackend(models.Model):
    _inherit = "netvisor.backend"

    def action_import_salary_types(self):
        """
        Import salary types from Netvisor
        :return:
        """
        _logger.debug(_("Importing salary types from Netvisor"))

        for record in self:
            endpoint = "payrollratiolist.nv"

            # Possible sources:
            # - tripexpensecustomlines
            # - taxingrules
            # - collectorratiolines
            # - userparameters
            # - companyparameters
            # - userformula
            # - tabledata
            # - foreclosure
            # - lowsalarysupport
            source = "userparameters"
            records = record._api_request_get(endpoint, params={"source": source})

            _logger.info("Found payroll ratio: {}".format(records))
            raise UserError(_("Importing payroll ratios is not implemented"))
