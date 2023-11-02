from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class NetvisorPartnerExportMapper(Component):
    _name = "netvisor.partner.export.mapper"
    _description = "Netvisor Partner Export Mapper"
    _inherit = "base.export.mapper"
    _usage = "export.mapper"
    _apply_on = ["netvisor.partner"]

    def export_customer(self, backend, record):
        """
        Export a partner as a customer to Netvisor
        :param backend: Netvisor backend record
        :param record: Partner record
        :return:
        """

        # Force record company for property fields
        if record.company_id:
            record = record.with_company(record.company_id.id)

        binding_model = self.env["netvisor.partner"]

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor.netvisor_customer", {"partner": record}
        )

        if binding:
            # Update existing record in Netvisor
            endpoint = f"customer.nv?method=edit&id={binding.external_id}"
            backend._api_request_post(endpoint, xml_string)
            msg = _(f"Updated partner '{record.display_name}'")
        else:
            # Create a new record to Netvisor
            res = backend._api_request_post("customer.nv?method=add", xml_string)

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

                msg = _(f"Created partner '{record.display_name}'")
            else:
                raise UserError(
                    _(
                        "Something went wrong when exporting customer. "
                        "Please see log for more details"
                    )
                )

        return msg
