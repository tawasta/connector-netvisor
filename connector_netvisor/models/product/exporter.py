from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


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
        values = self.map_record(record).values()
        client = backend.authenticate()
        binding_model = self.env["netvisor.product"]

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        if binding:
            # Update existing record in Netvisor
            client.products.update(binding.external_id, values)
            msg = _(f"Updated product '{record.display_name}'")
        else:
            res = client.products.create(values)

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

                msg = _(f"Created product '{record.display_name}'")
            else:
                raise UserError(
                    _(
                        "Something went wrong when exporting product. "
                        "Please see log for more details"
                    )
                )

        return msg

    @mapping
    def product_base_information(self, record):
        res = {
            "product_base_information": {
                "name": record.name or "",
                "product_code": record.default_code or "",
                "product_group": record.categ_id.name or "",
                # TODO: logic for what description to use
                "description": record.description_sale or "",
                "unit_price": {"amount": record.lst_price, "type": "net"},
                # "unit_weight": record.weight,
                "unit": record.uom_id.name,
                "purchase_price": record.standard_price,
                # "tariff_heading": TODO,
                # "comission_percentage": TODO,
                "is_active": record.active,
                "is_sales_product": record.sale_ok,
                # "inventory_enabled": TODO,
                # "country_of_origin": TODO,
            }
        }

        return res

    @mapping
    def product_bookkeeping_details(self, record):
        tax_ids = record.taxes_id

        if not tax_ids:
            tax = 0
        elif len(tax_ids) == 1:
            tax = tax_ids[0].amount
        else:
            raise ValidationError(_("Only one tax for product is supported"))

        code = record.property_account_income_id.code or False

        res = {
            "product_bookkeeping_details": {
                "default_vat_percentage": tax,
            }
        }

        if code:
            res["product_bookkeeping_details"]["default_domestic_account_number"] = code

        return res

    @mapping
    def product_additional_information(self, record):
        # Not implemented yet
        return

        # res = {}
        #
        # if record.weight:
        #     res["product_additional_information"] = {
        #         "product_gross_weight": {record.weight}
        #     }
        #
        # # TODO: product_net_weight
        # # TODO: product_weight_unit
        #
        # return res

    @mapping
    def product_package_information(self, record):
        # {
        #     "product_package_information": {
        #         "package_width": "",
        #         "package_height": "",
        #         "package_length": "",
        #     }
        # }

        # No mappings yet, so return nothing
        return
