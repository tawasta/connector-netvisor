from odoo.addons.component.core import Component


class NetvisorInvoiceExportMapper(Component):
    _inherit = "netvisor.invoice.export.mapper"

    def _get_dimensions(self, record):
        res = super()._get_dimensions(record)

        for analytic_tag in record.analytic_tag_ids:
            res.append(
                {
                    "dimension_name": analytic_tag.analytic_dimension_id.name,
                    "dimension_item": analytic_tag.name,
                }
            )

        return res
