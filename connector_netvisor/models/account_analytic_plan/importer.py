import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class NetvisorDimensionImportMapper(Component):
    _name = "netvisor.dimension.import.mapper"
    _description = "Netvisor Dimension Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.dimension"]

    def import_dimension(self, backend, dimension):
        """
        Import or update a dimension and its items from Netvisor
        :param backend: Netvisor backend record
        :param dimension: Dict with dimension information
        :return:
        """
        netvisor_model = self.env["netvisor.dimension"]
        odoo_model = self.env["account.analytic.plan"]
        values = self.map_record(dimension).values()
        netvisor_key = dimension.get("Netvisorkey")

        if not netvisor_key:
            # As the response dict should always have at least netvisor_key and name,
            # this error should never trigger
            raise MappingError(
                _("No netvisor key found for '{}'").format(dimension.get("Name"))
            )

        # Search for an existing binding
        existing_binding = netvisor_model.get_netvisor_binding(backend.id, netvisor_key)

        if existing_binding:
            # Binding exists: update values
            existing_binding.odoo_id.write(values)
            existing_record = existing_binding.odoo_id
            res = _(f"Updated values for dimension '{existing_binding.name}'")
        else:
            # No existing binding
            binding_values = {"backend_id": backend.id, "external_id": netvisor_key}

            # Search for existing dimension by exact name
            existing_record = odoo_model.search([("name", "=ilike", values["name"])])

            if existing_record:
                # Record was found but doesn't have a binding
                binding_values["odoo_id"] = existing_record.id
                netvisor_model.create(binding_values)
                existing_record.write(values)
                res = _(f"Updated values for dimension '{existing_record.name}'")
            else:
                # No dimension found. Create a new dimension and binding
                existing_record = odoo_model.create(values)
                binding_values["odoo_id"] = existing_record.id
                netvisor_model.create(binding_values)

                res = _(f"Created a new dimension '{existing_record.display_name}'")

        # Create individual jobs for creating the dimension items
        dimension_item = self.env["netvisor.dimension.item"]
        dimension_details = dimension.get("DimensionDetails")
        dimension_detail = (
            dimension_details.get("DimensionDetail") if dimension_details else {}
        )

        if isinstance(dimension_detail, dict):
            # If only one dimension detail is returned, it's not in a list
            dimension_detail = [dimension_detail]

        for item in dimension_detail:
            item["DimensionId"] = existing_record.id
            job_desc = _(
                "Netvisor: import dimension item '{}'".format(item.get("Name"))
            )
            dimension_item.with_delay(
                description=job_desc
            ).netvisor_import_dimension_item(item)

        return res

    # Netvisor, Odoo
    direct = [
        ("Name", "name"),
    ]
