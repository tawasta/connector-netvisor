import logging

from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class NetvisorPartnerImportMapper(Component):

    _name = "netvisor.partner.import.mapper"
    _description = "Netvisor Partner Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.partner"]

    def import_customer(self, backend, netvisor_key):
        """
        Import or update a customer from Netvisor
        :param backend: Netvisor backend record
        :param netvisor_key: Netvisor external ID
        :return:
        """
        netvisor_model = self.env["netvisor.partner"]
        odoo_model = self.env["res.partner"]

        endpoint = f"getcustomer.nv?id={netvisor_key}"
        partner = backend._api_request_get(endpoint)
        values = self.map_record(partner).values()
        existing_record = False

        # Omit empty values to avoid removing existing information from Odoo
        values = {k: v for k, v in values.items() if v}

        print(values)

        # Search for existing binding
        existing_binding = netvisor_model.search(
            [
                ("external_id", "=", netvisor_key),
                ("backend_id", "=", backend.id),
            ],
            limit=1,
        )

        if existing_binding:
            if existing_binding.backend_id.customer_import_update:
                # Binding exists: update values
                existing_binding.with_context(skip_export=True).write(values)
                return _(
                    "Updated values for partner '{}'".format(
                        existing_binding.display_name
                    )
                )
            else:
                return _("Did not update partner due to importer settings")

        # No existing binding
        binding_values = {"backend_id": backend.id, "external_id": netvisor_key}

        # 1. Search for existing partner by business and street
        if not existing_record and values.get("business_code") and values.get("street"):
            _logger.debug(_("Search for existing partner by business and street"))
            existing_record = odoo_model.search(
                [
                    ("business_code", "=", values["business_code"]),
                    ("street", "=ilike", values["street"]),
                ]
            )

        # 2. Search for existing partner by business id
        if not existing_record and values.get("business_code"):
            _logger.debug(_("Search for existing partner by business id"))
            existing_record = odoo_model.search(
                [("business_code", "=", values["business_code"])]
            )

        # 3. Search for existing partner by customer ref
        if not existing_record and values.get("ref"):
            _logger.debug(_("Search for existing partner by customer ref"))
            existing_record = odoo_model.search([("ref", "=", values["ref"])])

        # 4. Search for existing partner by email
        if not existing_record and values.get("email"):
            _logger.debug(_("Search for existing partner by email"))
            existing_record = odoo_model.search([("email", "=ilike", values["email"])])

        # 5. Search for existing partner by exact name and street
        if not existing_record and values.get("name") and values.get("street"):
            _logger.debug(_("Search for existing partner by name and street"))
            existing_record = odoo_model.search(
                [
                    ("name", "=ilike", values["name"]),
                    ("street", "=ilike", values["street"]),
                ]
            )

        if existing_record and len(existing_record) > 1:
            raise ValidationError(
                _(
                    f"Found multiple matching records: "
                    f"{existing_record.ids} with values {values}"
                )
            )

        if existing_record and backend.customer_import_update:
            # Partner was found but doesn't have a binding
            binding_values["odoo_id"] = existing_record.id
            netvisor_model.create(binding_values)
            try:
                existing_record.with_context(skip_export=True).write(values)
            except IntegrityError:
                # Binding already exists
                pass
            return _(
                "Updated values for partner '{}'".format(existing_record.display_name)
            )
        elif backend.customer_import_create:
            # No partner found. Create a new partner and binding
            existing_record = odoo_model.with_context(skip_export=True).create(values)
            binding_values["odoo_id"] = existing_record.id
            netvisor_model.create(binding_values)

            return _("Created a new partner '{}'".format(existing_record.display_name))
        else:
            return _("Did not create or update partner due to importer settings")

    # Netvisor, Odoo
    @mapping
    def name(self, record):
        res = {"name": record.get("CustomerBaseInformation", {}).get("Name")}

        return res

    @mapping
    def name_extension(self, record):
        res = {
            "name_extension": record.get("CustomerBaseInformation", {}).get(
                "NameExtension"
            )
        }

        return res

    @mapping
    def business_code(self, record):
        res = {}
        business_code = record.get("CustomerBaseInformation", {}).get(
            "ExternalIdentifier"
        )
        if business_code:
            res.update({"business_code": business_code, "is_company": True})

        return res

    @mapping
    def active(self, record):
        res = {"active": record.get("CustomerBaseInformation", {}).get("IsActive")}

        return res

    @mapping
    def street(self, record):
        res = {
            "street": record.get("CustomerBaseInformation", {}).get("StreetAddress")
        }

        return res

    @mapping
    def street2(self, record):
        res = {
            "street2": record.get("CustomerBaseInformation", {}).get(
                "AdditionalStreetAddress"
            )
        }

        return res

    @mapping
    def city(self, record):
        res = {"city": record.get("CustomerBaseInformation", {}).get("City")}

        return res

    @mapping
    def zip(self, record):
        res = {"zip": record.get("CustomerBaseInformation", {}).get("PostNumber")}

        return res

    @mapping
    def country_id(self, record):
        Country = self.env["res.country"]
        country_code = record.get("CustomerBaseInformation", {}).get("Country")
        res = {}

        if country_code:
            country_id = Country.search(
                [
                    ("code", "=", country_code),
                ],
                limit=1,
            )

            res["country_id"] = country_id.id

        return res

    @mapping
    def comment(self, record):
        res = {
            "comment": record.get("CustomerBaseInformation", {}).get("Comment")
        }

        return res

    @mapping
    def ref(self, record):
        res = {
            "ref": record.get("CustomerBaseInformation", {}).get(
                "ReferenceNumber"
            )
        }

        return res

    @mapping
    def website(self, record):
        res = {
            "website": record.get("CustomerBaseInformation", {}).get("HomePageUri")
        }

        return res

    @mapping
    def email(self, record):
        res = {"email": record.get("CustomerBaseInformation", {}).get("Email")}

        return res

    @mapping
    def email_invoicing_address(self, record):
        res = {
            "email_invoicing_address": record.get("CustomerBaseInformation", {}).get(
                "EmailInvoicingAddress"
            )
        }

        return res

    @mapping
    def phone(self, record):
        res = {"phone": record.get("CustomerBaseInformation", {}).get("PhoneNumber")}

        return res

    @mapping
    def edicode(self, record):
        res = {
            "edicode": record.get("CustomerFinvoiceDetails", {}).get(
                "FinvoiceAddress"
            )
        }

        return res

    @mapping
    def einvoice_operator_id(self, record):
        res = {}
        operator_code = record.get("CustomerFinvoiceDetails", {}).get(
            "FinvoiceRouterCode"
        )
        operator_id = self.env["res.partner.operator.einvoice"].search(
            [("identifier", "=", operator_code)]
        )

        if operator_code and operator_id:
            res = {"einvoice_operator_id": operator_id.id}

        return res
