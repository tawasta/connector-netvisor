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

    def import_supplier(self, backend, netvisor_key):
        endpoint = f"getvendor.nv?netvisorkey={netvisor_key}"
        return self.import_partner(backend, netvisor_key, endpoint)

    def import_customer(self, backend, netvisor_key):
        endpoint = f"getcustomer.nv?id={netvisor_key}"
        return self.import_partner(backend, netvisor_key, endpoint)

    # TODO: Add helper functions to reduce complexity
    # flake8: noqa: C901
    def import_partner(self, backend, netvisor_key, endpoint):
        """
        Import or update a partner from Netvisor
        :param backend: Netvisor backend record
        :param netvisor_key: Netvisor external ID
        :return:
        """
        netvisor_model = self.env["netvisor.partner"]
        odoo_model = self.env["res.partner"]

        partner = backend._api_request_get(endpoint)
        values = self.map_record(partner).values()
        existing_record = False

        if endpoint.startswith("getcustomer.nv"):
            import_update = backend.customer_import_update
            import_create = backend.customer_import_create
        else:
            import_update = backend.supplier_import_update
            import_create = backend.supplier_import_create

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
            existing_record = existing_binding.odoo_id

        # No existing binding
        binding_values = {"backend_id": backend.id, "external_id": netvisor_key}

        # 1. Search for existing partner by business and street
        if (
            not existing_record
            and values.get("company_registry")
            and values.get("street")
        ):
            _logger.debug(_("Search for existing partner by business and street"))
            existing_record = odoo_model.search(
                [
                    ("company_registry", "=", values["company_registry"]),
                    ("street", "=ilike", values["street"]),
                ]
            )

        # 2. Search for existing partner by business id
        if not existing_record and values.get("company_registry"):
            _logger.debug(_("Search for existing partner by business id"))
            existing_record = odoo_model.search(
                [("company_registry", "=", values["company_registry"])]
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
                    "Found multiple matching records: " "{} with values {}".format(
                        existing_record.ids, values
                    )
                )
            )

        if existing_record and import_update:
            if not existing_binding:
                # Partner was found but doesn't have a binding
                binding_values["odoo_id"] = existing_record.id
                existing_binding = netvisor_model.create(binding_values)
            try:
                if (
                    endpoint.startswith("getcustomer.nv")
                    and not existing_record.customer_rank
                ):
                    values["customer_rank"] = 1
                elif (
                    endpoint.startswith("getvendor.nv")
                    and not existing_record.supplier_rank
                ):
                    values["supplier_rank"] = 1

                existing_record.with_context(skip_export=True).write(values)
            except IntegrityError:
                # Binding already exists
                pass
            return _(
                "Updated values for partner '{}' with ID {}".format(
                    existing_record.display_name, existing_record.id
                )
            )
        elif import_create:
            # No partner found. Create a new partner and binding
            if endpoint.startswith("getcustomer.nv"):
                values["customer_rank"] = 1
            elif endpoint.startswith("getvendor.nv"):
                values["supplier_rank"] = 1

            existing_record = odoo_model.with_context(skip_export=True).create(values)
            binding_values["odoo_id"] = existing_record.id
            netvisor_model.create(binding_values)

            return _(
                "Created a new partner '{}' with ID {}".format(
                    existing_record.display_name, existing_record.id
                )
            )
        else:
            return _("Did not create or update partner due to importer settings")

    # Netvisor, Odoo
    def _get_partner_base(self, record):
        return (
            record.get("CustomerBaseInformation")
            or record.get("VendorBaseInformation")
            or {}
        )

    @mapping
    def name(self, record):
        res = {"name": self._get_partner_base(record).get("Name")}

        return res

    @mapping
    def name_extension(self, record):
        res = {"name_extension": self._get_partner_base(record).get("NameExtension")}

        return res

    @mapping
    def company_registry(self, record):
        res = {}
        company_registry = self._get_partner_base(record).get("ExternalIdentifier")
        if company_registry:
            res.update({"company_registry": company_registry, "is_company": True})

        return res

    @mapping
    def active(self, record):
        res = {"active": self._get_partner_base(record).get("IsActive")}

        return res

    @mapping
    def street(self, record):
        res = {"street": self._get_partner_base(record).get("StreetAddress")}

        return res

    @mapping
    def street2(self, record):
        res = {"street2": self._get_partner_base(record).get("AdditionalStreetAddress")}

        return res

    @mapping
    def city(self, record):
        res = {"city": self._get_partner_base(record).get("City")}

        return res

    @mapping
    def zip(self, record):
        res = {"zip": self._get_partner_base(record).get("PostNumber")}

        return res

    @mapping
    def country_id(self, record):
        Country = self.env["res.country"]
        country_code = self._get_partner_base(record).get("Country")
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
        res = {"comment": self._get_partner_base(record).get("Comment")}

        return res

    @mapping
    def ref(self, record):
        res = {"ref": self._get_partner_base(record).get("ReferenceNumber")}

        return res

    @mapping
    def website(self, record):
        res = {"website": self._get_partner_base(record).get("HomePageUri")}

        return res

    @mapping
    def email(self, record):
        res = {"email": self._get_partner_base(record).get("Email")}

        return res

    @mapping
    def email_invoicing_address(self, record):
        res = {
            "email_invoicing_address": self._get_partner_base(record).get(
                "EmailInvoicingAddress"
            )
        }

        return res

    @mapping
    def phone(self, record):
        res = {"phone": self._get_partner_base(record).get("PhoneNumber")}

        return res

    @mapping
    def edicode(self, record):
        res = {"edicode": self._get_partner_base(record).get("FinvoiceAddress")}

        return res

    @mapping
    def einvoice_operator_id(self, record):
        res = {}
        operator_code = self._get_partner_base(record).get("FinvoiceRouterCode")
        operator_id = self.env["res.partner.operator.einvoice"].search(
            [("identifier", "=", operator_code)]
        )

        if operator_code and operator_id:
            res = {"einvoice_operator_id": operator_id.id}

        return res
