from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.component.core import Component


class NetvisorPaymentExportMapper(Component):
    _name = "netvisor.payment.export.mapper"
    _description = "Netvisor Payment Export Mapper"
    _inherit = "base.export.mapper"
    _usage = "export.mapper"
    _apply_on = ["netvisor.payment"]

    def export_payment(self, backend, record):
        """
        Export a payment to Netvisor
        :param backend: Netvisor backend record
        :param record: Payment record
        :return:
        """
        # Force record company for property fields
        if record.company_id:
            record = record.with_company(record.company_id.id)
        binding_model = self.env["netvisor.payment"]

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor.netvisor_payment", {"record": record}
        )

        if binding:
            raise ValidationError(_("This payment is already sent to Netvisor!"))
        else:
            res = backend._api_request_post("payment.nv", xml_string)

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

                msg = _(f"Created payment '{record.display_name}'")
            else:
                raise UserError(
                    _(
                        "Something went wrong when exporting payment. "
                        "Please see log for more details"
                    )
                )

        return msg
