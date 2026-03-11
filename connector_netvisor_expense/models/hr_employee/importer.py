import logging

from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class NetvisorEmployeeImportMapper(Component):
    _name = "netvisor.employee.import.mapper"
    _description = "Netvisor Employee Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.employee"]

    def import_employee(self, backend, netvisor_key):
        """
        Import or update an employee from Netvisor
        :param backend: Netvisor backend record
        :param netvisor_key: Netvisor external ID
        :return:
        """
        netvisor_model = self.env["netvisor.employee"]
        odoo_model = self.env["hr.employee"]
        endpoint = f"getemployee.nv?netvisorkey={netvisor_key}"

        employee = backend._api_request_get(endpoint)
        values = self.map_record(employee).values()
        existing_record = False

        # Search for existing binding
        existing_binding = netvisor_model.search(
            [
                ("external_id", "=", netvisor_key),
                ("backend_id", "=", backend.id),
            ],
            limit=1,
        )

        if existing_binding:
            existing_record = existing_binding.odoo_id

        # No existing binding
        binding_values = {"backend_id": backend.id, "external_id": netvisor_key}

        # 1. Search for existing employee using Employee ID
        if not existing_record and values.get("identification_id"):
            _logger.debug(_("Search for existing employee using Employee ID"))
            existing_record = odoo_model.search(
                [("identification_id", "=", values["identification_id"])]
            )

        # 2. Search for existing employee using SSN
        if not existing_record and values.get("ssnid"):
            _logger.debug(_("Search for existing employee using SSN"))
            existing_record = odoo_model.search([("ssnid", "=", values["ssnid"])])

        if existing_record and len(existing_record) > 1:
            raise ValidationError(
                _("Found multiple matching records: %s", existing_record.ids)
            )

        if not existing_record:
            existing_record = self.env["hr.employee"].sudo().create(values)

        if not existing_binding:
            # Record was found but doesn't have a binding
            binding_values["odoo_id"] = existing_record.id
            existing_binding = netvisor_model.create(binding_values)
        try:
            existing_record.with_context().write(values)
        except IntegrityError:
            # Binding already exists
            pass

        return _(
            "Updated values for employee '{}' with ID {}".format(
                existing_record.display_name, existing_record.id
            )
        )

    # Netvisor, Odoo
    direct = []

    def _get_base_information(self, record):
        return record.get("employeebaseinformation", {})

    @mapping
    def ssnid(self, record):
        base_info = self._get_base_information(record)
        employee_identifier = base_info.get("employeeidentifier", {})

        res = {}

        if employee_identifier.get("@type") == "number":
            res["identification_id"] = employee_identifier.get("#text")
        elif employee_identifier.get("@type") == "finnishidentifier":
            res["ssnid"] = employee_identifier.get("#text")

        return res

    @mapping
    def identification_id(self, record):
        base_info = self._get_base_information(record)
        res = {"identification_id": base_info.get("employeenumber")}

        return res

    @mapping
    def firstname(self, record):
        base_info = self._get_base_information(record)
        res = {"firstname": base_info.get("firstname")}

        return res

    @mapping
    def lastname(self, record):
        base_info = self._get_base_information(record)
        res = {"lastname": base_info.get("lastname")}

        return res
