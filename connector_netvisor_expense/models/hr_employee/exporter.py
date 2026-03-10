import logging

from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class NetvisorEmployeeExportMapper(Component):
    _name = "netvisor.employee.export.mapper"
    _description = "Netvisor Employee Export Mapper"
    _inherit = "base.export.mapper"
    _usage = "export.mapper"
    _apply_on = ["netvisor.employee"]

    def export_employee(self, backend, record):
        """
        Export an employee to Netvisor
        :param backend: Netvisor backend record
        :param record: Employee record
        :return:
        """

        # Force record company for property fields
        if record.company_id:
            record = record.with_company(record.company_id.id)

        self._validate(record)

        binding_model = self.env["netvisor.employee"]

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor_expense.netvisor_employee",
            {
                "record": record,
            },
        )

        msg = ""

        if not binding:
            # TODO / FYI: This is dumb, because getemployee.nv endpoint doesn't return
            # the employee ID or Netvisor ID.
            # We currently can't check if the employee already exists in Netvisor.
            # If searching by SSN is possible later, this could be improved to first
            # check if the employee exists, instead of trying blindly.
            try:
                # Create a new record to Netvisor
                method = "add"
                backend._api_request_post(
                    "employee.nv",
                    xml_string,
                    params={"Method": method}
                )
                msg = _("Exported employee to Netvisor")
            except Exception as e:
                # The API returns an error if the employee already exists,
                # so we try to edit instead
                _logger.info(e)
                method = "edit"
                try:
                    backend._api_request_post(
                        "employee.nv",
                        xml_string,
                        params={"Method": method}
                    )
                    msg = _("Exported employee information to Netvisor")
                except Exception as edit_error:
                    raise UserError(_(
                        "Failed to export employee '%s' to Netvisor: %s",
                        record.display_name, str(edit_error)
                    )) from edit_error

            record.message_post(body=msg)

            # employee.nv returns nothing, so we assume that the employee 
            # was created successfully if no error is raised.
            # We can't make a binding, and the matching will be done by SSN         

        return msg

    def _validate(self, record):
        if not record.get_social_security_number():
            raise UserError(
                _("Employee '%s' does not have a social security number, " \
                "which is required for exporting to Netvisor", record.display_name)
            )

        if record.bank_account_id and not record.bank_account_id.allow_out_payment:
            raise UserError(
                _("Employee '%s' has a bank account '%s' " \
                "that is not allowed for outgoing payments. "
                "Please set the bank account as trusted first.",
                record.display_name,
                record.bank_account_id.acc_number
                )
            )
