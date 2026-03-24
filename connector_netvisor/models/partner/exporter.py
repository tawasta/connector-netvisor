import logging

from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


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

        if not record.netvisor_export:
            return _("Exporting to Netvisor is disabled for this partner.")

        if len(self.env["res.partner"].search([("ref", "=", record.ref)])) > 1:
            raise UserError(
                _(
                    "Multiple partners found with the same reference "
                    "'%s'. Cannot determine the correct "
                    "Netvisor customer to update.",
                    record.ref,
                )
            )

        # Force record company for property fields
        if record.company_id:
            record = record.with_company(record.company_id.id)

        binding_model = self.env["netvisor.partner"].with_context(active_test=False)

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor.netvisor_customer", {"partner": record}
        )

        if not binding:
            # Try to get existing partner and create a binding
            endpoint = "customerlist.nv"
            params = {"keyword": record.ref}
            customers = backend._api_request_get(endpoint, params)
            _logger.warning(f"Found partner(s) data: {customers}")

            for customer in customers:
                if customer.get("Code") == record.ref:
                    # Match found. Create a new binding
                    binding = binding_model.create(
                        {
                            "backend_id": backend.id,
                            "external_id": customer.get("Netvisorkey"),
                            "odoo_id": record.id,
                        }
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
