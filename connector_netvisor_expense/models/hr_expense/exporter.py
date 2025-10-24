import logging

from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class NetvisorExpenseExportMapper(Component):
    _name = "netvisor.expense.export.mapper"
    _description = "Netvisor Expense Export Mapper"
    _inherit = "base.export.mapper"
    _usage = "export.mapper"
    _apply_on = ["netvisor.expense"]

    def export_expense(self, backend, record):
        """
        Export an expense to Netvisor
        :param backend: Netvisor backend record
        :param record: Expense record
        :return:
        """

        # Force record company for property fields
        if record.company_id:
            record = record.with_company(record.company_id.id)

        binding_model = self.env["netvisor.expense"]

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

        analytic_accounts = self.env["account.analytic.account"].search([])
        dimensions = dict(
            [(r.id, (r.root_plan_id.name, r.name)) for r in analytic_accounts]
        )

        custom_lines = record.filtered(
            lambda r: r.product_id.netvisor_expense_type == "custom"
        )
        travel_lines = record.filtered(
            lambda r: r.product_id.netvisor_expense_type == "travel"
        )
        # Daily compensation lines
        daily_lines = record.filtered(
            lambda r: r.product_id.netvisor_expense_type == "daily"
        )

        xml_string = self.env["ir.qweb"]._render(
            "connector_netvisor_expense.netvisor_tripexpense",
            {
                "record": record,
                "dimensions": dimensions,
                "custom_lines": custom_lines,
                "travel_lines": travel_lines,
                "daily_lines": daily_lines,
            },
        )

        msg = ""

        if not binding:
            # Create a new record to Netvisor
            res = backend._api_request_post("tripexpense.nv", xml_string)

            if res:
                try:
                    binding_model.create(
                        {
                            "backend_id": backend.id,
                            "external_id": res.get("InsertedDataIdentifier"),
                            "odoo_id": record.id,
                        }
                    )
                    msg = _("Expense posted to Netvisor")
                    record.message_post(body=msg)

                except IntegrityError:
                    # Binding already exists
                    pass

                msg = _("Created expense '{}'".format(record.display_name))
            else:
                raise UserError(
                    _(
                        "Something went wrong when exporting customer. "
                        "Please see log for more details"
                    )
                )

        return msg
