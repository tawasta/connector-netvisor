from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component


class NetvisorProductExportMapper(Component):
    _name = "netvisor.product.export.mapper"
    _description = "Netvisor Product Export Mapper"
    _inherit = "base.export.mapper"
    _usage = "export.mapper"
    _apply_on = ["netvisor.product"]

    def export_product(self, backend, record):
        """
        Export a product to Netvisor
        :param backend: Netvisor backend record
        :param record: Product record
        :return:
        """
        # Force record company for property fields
        if record.company_id:
            record = record.with_company(record.company_id.id)
        binding_model = self.env["netvisor.product"].with_context(active_test=False)

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor.netvisor_product", {"product": record}
        )

        if binding:
            # Update existing record in Netvisor
            endpoint = f"product.nv?method=edit&id={binding.external_id}"
            backend._api_request_post(endpoint, xml_string)
            msg = _(f"Updated product '{record.display_name}'")
        else:
            res = backend._api_request_post("product.nv?method=add", xml_string)

            if res:
                try:
                    binding_model.create(
                        {
                            "backend_id": backend.id,
                            "external_id": res.get("InsertedDataIdentifier"),
                            "odoo_id": record.id,
                        }
                    )
                except IntegrityError:
                    # Binding already exists
                    pass

                msg = _(f"Created product '{record.display_name}'")
            else:
                raise UserError(
                    _(
                        "Something went wrong when exporting product. "
                        "Please see log for more details"
                    )
                )

        return msg
