import logging

from odoo import _

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class NetvisorDimensionItemImportMapper(Component):

    _name = "netvisor.dimension.item.import.mapper"
    _description = "Netvisor Dimension Item Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.dimension.item"]

    def import_dimension(self, backend, dimension_item):
        """
        Import or update a dimension items from a dict
        :param dimension_item: Dict with dimension item information
        :return:
        """
        netvisor_model = self.env["netvisor.dimension.item"]
        odoo_model = self.env["account.analytic.tag"]
        netvisor_key = dimension_item.get("netvisor_key")
        values = {
            "analytic_dimension_id": dimension_item.get("dimension_id"),
            "name": dimension_item.get("name"),
        }

        # Search for an existing binding
        existing_binding = netvisor_model.get_netvisor_binding(backend.id, netvisor_key)

        if existing_binding:
            # Binding exists: update values
            existing_binding.odoo_id.write(values)
            return _(
                "Updated values for dimension item '{}'".format(existing_binding.name)
            )
        else:
            # No existing binding
            binding_values = {"backend_id": backend.id, "external_id": netvisor_key}

            # Search for existing dimension item by exact name
            existing_record = odoo_model.search([("name", "=ilike", values["name"])])

            if existing_record:
                # Record was found but doesn't have a binding
                binding_values["odoo_id"] = existing_record.id
                netvisor_model.create(binding_values)
                existing_record.write(values)
                return _(
                    "Updated values for dimension item '{}'".format(
                        existing_record.name
                    )
                )
            else:
                # No dimension found. Create a new dimension and binding
                existing_record = odoo_model.create(values)
                binding_values["odoo_id"] = existing_record.id
                netvisor_model.create(binding_values)

                return _(
                    "Created a new dimension item '{}'".format(
                        existing_record.display_name
                    )
                )

    # Netvisor, Odoo
    direct = [
        ("dimension_id", "analytic_dimension_id"),
        ("name", "name"),
    ]
