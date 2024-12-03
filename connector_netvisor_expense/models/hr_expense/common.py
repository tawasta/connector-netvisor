from odoo import _, api, fields, models


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
            netvisor_model = self.env["netvisor.expense"]

            if not company_id and record.company_id:
                company_id = record.company_id.id
            elif not company_id:
                company_id = self.env.user.company_id.id

            if company_id:
                netvisor_model = netvisor_model.with_context(company_id=company_id)

            if use_queue:
                # Queued sending
                job_desc = _("Netvisor: export expense '{}'".format(record.name))
                netvisor_model.with_delay(description=job_desc).netvisor_export_expense(
                    record, company_id
                )
            else:
                # Immediate sending
                netvisor_model.netvisor_export_expense(record, company_id)
