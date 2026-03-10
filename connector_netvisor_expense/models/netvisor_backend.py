import logging

from odoo import _, models
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

            _logger.info(f"Found payroll ratio: {records}")
            raise UserError(_("Importing payroll ratios is not implemented"))

    def action_import_employees(self):
        """
        Import employees from Netvisor
        :return:
        """
        endpoint = "getemployees.nv"
        include_ended_employments = 0
        for record in self:
            records = record._api_request_get(
                endpoint, params={"includeendedemployments": include_ended_employments}
            )

            _logger.info(f"Found employees: {records}")
            # TODO: actually import the customers
            raise UserError(_("Importing employees is not implemented"))
