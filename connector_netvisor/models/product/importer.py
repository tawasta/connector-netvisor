import logging
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, changed_by
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class NetvisorProductImportMapper(Component):

    _name = "netvisor.product.import.mapper"
    _description = "Netvisor Product Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.product"]

    def import_product(self, backend, netvisor_key):
        """
        Import or update a product from Netvisor
        :param backend: Netvisor backend record
        :param netvisor_key: Netvisor id
        :return:
        """
        netvisor_model = self.env["netvisor.product"]
        odoo_model = self.env["product.product"]
        client = backend.authenticate()
        product = client.products.get(netvisor_key)
        values = self.map_record(product).values()
        values["company_id"] = backend.company_id.id

        existing_record = False

        # Omit empty values to avoid removing existing information from Odoo
        values = {k: v for k, v in values.items() if v}

        # Search for existing binding
        existing_binding = netvisor_model.search(
            [
                ("external_id", "=", netvisor_key),
                ("backend_id", "=", backend.id),
            ],
            limit=1,
        )

        if existing_binding:
            if existing_binding.backend_id.partner_import_update:
                # Binding exists: update values
                existing_binding.odoo_id.with_context(skip_export=True).write(values)
                return _(
                    "Updated values for product '{}'".format(
                        existing_binding.display_name
                    )
                )
            else:
                return _("Did not update product due to importer settings")

        # No existing binding
        binding_values = {"backend_id": backend.id, "external_id": netvisor_key}

        # Search for existing product by default code or exact name
        if values.get("default_code"):
            existing_record = odoo_model.search(
                [
                    "|",
                    ("default_code", "=", values["default_code"]),
                    ("name", "=ilike", values["name"]),
                ]
            )

        if existing_record and len(existing_record) > 1:
            raise ValidationError(
                _(
                    f"Found multiple matching records: {existing_record.ids} with values {values}"
                )
            )

        if existing_record:
            # Record was found but doesn't have a binding
            binding_values["odoo_id"] = existing_record.id
            existing_binding = netvisor_model.create(binding_values)

            if existing_binding.backend_id.customer_import_update:
                existing_binding.with_context(skip_export=True).write(values)
                return _(
                    "Updated values for product '{}'".format(
                        existing_binding.display_name
                    )
                )
        elif backend.customer_import_create:
            # No product found. Create a new product and binding
            existing_record = odoo_model.with_context(skip_export=True).create(values)
            binding_values["odoo_id"] = existing_record.id
            netvisor_model.create(binding_values)

            return _("Created a new product '{}'".format(existing_record.display_name))
        else:
            return _("Did not create or update product due to importer settings")

    @mapping
    def name(self, record):
        res = {"name": record.get("product_base_information", {}).get("name")}

        return res

    @mapping
    def description_sale(self, record):
        res = {
            "description_sale": record.get("product_base_information", {}).get(
                "description"
            )
        }

        return res

    @mapping
    def default_code(self, record):
        res = {
            "default_code": record.get("product_base_information", {}).get(
                "product_code"
            )
        }

        return res

    @mapping
    def weight(self, record):
        res = {"weight": record.get("product_base_information", {}).get("unit_weight")}

        return res

    @mapping
    def sale_ok(self, record):
        res = {
            "sale_ok": record.get("product_base_information", {}).get(
                "is_sales_product"
            )
        }

        return res

    @mapping
    def standard_price(self, record):
        res = {
            "standard_price": record.get("product_base_information", {}).get(
                "purchase_price"
            )
        }

        return res

    @mapping
    def standard_price(self, record):
        res = {
            "standard_price": record.get("product_base_information", {}).get(
                "purchase_price"
            )
        }

        return res

    @mapping
    def active(self, record):
        res = {"active": record.get("product_base_information", {}).get("is_active")}

        return res

    @mapping
    def lst_price(self, record):
        res = {
            "lst_price": record.get("product_base_information", {})
            .get("unit_price")
            .get("amount")
        }

        return res

    @mapping
    def categ_id(self, record):
        category_name = record.get("product_base_information", {}).get("product_group")

        if not category_name:
            return

        product_category = self.env["product.category"]
        category_id = product_category.search([("name", "=ilike", category_name)])

        if not category_id:
            # Create a new category
            category_id = product_category.create({"name": category_name})

        return {"categ_id": category_id.id}

    @mapping
    def uom_id(self, record):
        uom_name = record.get("product_base_information", {}).get("unit")

        if not uom_name:
            return

        res = {}

        # The search could also try to search units with language (Finnish) in context,
        # for better results
        uom_id = self.env["uom.uom"].search([("name", "=ilike", uom_name)])

        if uom_id:
            res["uom_id"] = uom_id.id
            res["uom_po_id"] = uom_id.id

        return res

    @mapping
    def taxes_id(self, record):
        tax = record.get("product_book_keeping_details", {}).get("default_vat_percent")

        if not tax:
            return

        res = {}

        # TODO: This can be inaccurate when multiple taxes have same amount
        tax_id = self.env["account.tax"].search(
            [
                ("type_tax_use", "in", ["sale", "none"]),
                ("amount", "=", tax),
                ("amount_type", "=", "percent"),
                ("price_include", "=", False),
            ],
            limit=1,
        )

        if tax_id:
            res["taxes_id"] = tax_id

        return res

    @mapping
    def property_account_income_id(self, record):
        account_number = record.get("product_book_keeping_details", {}).get(
            "default_domestic_account_number"
        )

        if not account_number:
            return

        res = {}

        account_id = self.env["account.account"].search(
            [("code", "=", account_number)], limit=1
        )

        if account_id:
            res["property_account_income_id"] = account_id.id

        return res
