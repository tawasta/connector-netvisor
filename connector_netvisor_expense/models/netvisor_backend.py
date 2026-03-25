import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NetvisorBackend(models.Model):
    _inherit = "netvisor.backend"

    include_ended_employments = fields.Boolean(default=False)

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

            _logger.info("Found payroll ratios: %s", records)
            raise UserError(_("Importing payroll ratios is not implemented"))

    def action_import_employees(self):
        """
        Import employees from Netvisor
        :return:
        """
        endpoint = "getemployees.nv"
        NetvisorEmployee = self.env["netvisor.employee"]

        employee_count = 0

        for record in self:
            params = {
                "includeendedemployments": 1 if record.include_ended_employments else 0
            }

            employees = record._api_request_get(endpoint, params=params)
            employee_count += len(employees)

            _logger.info(f"Found {len(employees)} employees from Netvisor")
            for employee in employees:
                netvisor_key = employee.get("netvisorkey", "Unknown")
                job_desc = _(
                    "Netvisor: import employee '%(name)s' using Netvisor ID %(key)s",
                    name=employee.get("realname", "Unknown"),
                    key=netvisor_key,
                )
                NetvisorEmployee.with_delay(
                    description=job_desc
                ).netvisor_import_employee(netvisor_key)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import started"),
                "message": _(
                    "Importing %d employees in the background...", employee_count
                ),
                "type": "success",
                "sticky": False,
            },
        }
