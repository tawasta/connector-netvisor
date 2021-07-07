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
        values = self.map_record(record).values()
        client = backend.authenticate()
        binding_model = self.env["netvisor.partner"]

        binding = binding_model.search([("odoo_id", "=", record.id)])

        if binding:
            # Update existing record in Netvisor
            client.customers.update(binding.external_id, values)
            msg = _(f"Updated partner '{record.display_name}'")
        else:
            res = client.customers.create(values)

            if res:
                binding_model.create(
                    {
                        "backend_id": backend.id,
                        "external_id": res,
                        "odoo_id": record.id,
                    }
                )

                msg = _(f"Created partner '{record.display_name}'")
            else:
                raise UserError(
                    _(
                        "Something went wrong when exporting customer. "
                        "Please see log for more details"
                    )
                )

        return msg

    @mapping
    def customer_base_information(self, record):
        res = {
            "customer_base_information": {
                "name": record.name or "",
                # Using "ref" as internal identifier is somewhat open to
                # interpretation. Ref can also be used for customer-specific
                # reference number
                "internal_identifier": record.ref or "",
                "external_identifier": record.business_code or "",
                "is_active": record.active or "",
                "street_address": record.get_combined_street(),
                "city": record.city or "",
                "post_number": record.zip or "",
                "country": record.country_id.code or "",
                "home_page_uri": record.website or "",
                "email": record.email or "",
                "email_invoicing_address": record.email or "",
                "phone_number": record.phone or "",
            }
        }

        return res

    @mapping
    def customer_additional_information(self, record):
        res = {
            "customer_additional_information": {
                "comment": record.comment or "",
                # "reference_number": record.ref or "",
            }
        }

        return res

    @mapping
    def customer_finvoice_details(self, record):
        res = {
            "customer_finvoice_details": {
                "finvoice_address": record.edicode or "",
                "finvoice_router_code": record.einvoice_operator_id.identifier or "",
            }
        }

        return res
