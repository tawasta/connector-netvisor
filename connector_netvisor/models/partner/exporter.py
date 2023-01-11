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

        values = self.map_record(record).values()
        client = backend.authenticate()
        binding_model = self.env["netvisor.partner"]

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor.customer", values
        )
        print(xml_string)
        return

        if binding:
            # Update existing record in Netvisor
            backend._api_request_post("customer.nv", values, {'method': 'Edit', 'id': binding.external_id})
            msg = _(f"Updated partner '{record.display_name}'")
        else:
            # Create a new record to Netvisor
            res = backend._api_request_post("customer.nv", values, {'method': 'Add'})
            print(res)

            if res:
                try:
                    binding_model.create(
                        {
                            "backend_id": backend.id,
                            "external_id": res,
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

    @mapping
    def customer_base_information(self, record):
        if (
            record.commercial_partner_id.id != record.id
            and record.commercial_partner_id.ref != record.ref
        ):
            # Using "ref" as internal identifier is somewhat open to
            # interpretation. Ref can also be used for customer-specific
            # reference number.
            ref = record.ref
        else:
            # Skip sending ref if commercial partner (contact company) has the same ref.
            # Netvisor won't allow duplicate customer references
            ref = ""

        res = {
            "customer_base_information": {
                "name": record.name or "",
                "name_extension": record.name_extension or "",
                "internal_identifier": ref,
                "external_identifier": record.business_code or "",
                "is_active": record.active or "",
                "street_address": record.street or "",
                "additional_address_line": record.street2 or "",
                "city": record.city or "",
                "post_number": record.zip or "",
                "country": record.country_id.code or "",
                "home_page_uri": record.website or "",
                "email": record.email or "",
                "email_invoicing_address": record.email_invoicing_address or "",
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
        res = {}
        if record.company_type == "company":
            res = {
                "customer_finvoice_details": {
                    "finvoice_address": record.edicode or "",
                    "finvoice_router_code": record.einvoice_operator_id.identifier
                    or "",
                }
            }

        return res
