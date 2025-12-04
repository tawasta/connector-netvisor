from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.expense",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    def action_netvisor_export_record(self, use_queue=False, company_id=False):
        """
        Export record to Netvisor
        :return:
        """
        for record in self:
            expense_type = record.product_id.netvisor_expense_type
            if not expense_type:
                raise ValidationError(
                    _(
                        "Netvisor expense type is missing from product '%s'"
                        % record.product_id.name
                    )
                )

            if expense_type == "travel" and not record.product_id.netvisor_travel_type:
                raise ValidationError(
                    _(
                        "Travel type is missing from product '%s'"
                        % record.product_id.name
                    )
                )
            elif (
                expense_type == "daily"
                and not record.product_id.netvisor_compensation_type
            ):
                raise ValidationError(
                    _(
                        "Compensation type is missing from product '%s'"
                        % record.product_id.name
                    )
                )

            netvisor_model = self.env["netvisor.expense"]

            if not company_id and record.company_id:
                company_id = record.company_id.id
            elif not company_id:
                company_id = self.env.user.company_id.id

            if company_id:
                netvisor_model = netvisor_model.with_context(company_id=company_id)

            if use_queue:
                # Queued sending
                job_desc = _(f"Netvisor: export expense '{record.name}'")
                netvisor_model.with_delay(description=job_desc).netvisor_export_expense(
                    record, company_id
                )
            else:
                # Immediate sending
                netvisor_model.netvisor_export_expense(record, company_id)
