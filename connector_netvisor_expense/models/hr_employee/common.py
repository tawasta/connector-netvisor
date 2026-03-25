from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.employee",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    job_begin_date = fields.Date(
        string="Job begin date",
        default=fields.Date.context_today,
    )

    def get_social_security_number(self):
        """
        Get the employee's social security number (SSN)
        :return: SSN or None

        The point of this method is to allow overriding the logic for getting the SSN,
        as in some cases it might be stored in a different field or require formatting.
        """
        self.ensure_one()

        return self.ssnid

    def action_netvisor_export_record(self, use_queue=False, company_id=False):
        """
        Export record to Netvisor
        :return:
        """
        netvisor_model = self.env["netvisor.employee"]

        for record in self:
            if company_id:
                # Prefer overridden company ID
                effective_company_id = company_id
            elif not company_id and record.company_id:
                # Fallback to record company ID if no overridden company ID is provided
                effective_company_id = record.company_id.id
            else:
                # Fallback to user's company ID if no record company ID is set
                effective_company_id = self.env.user.company_id.id

            netvisor_model = netvisor_model.with_context(
                company_id=effective_company_id
            )

            if use_queue:
                # Queued sending
                job_desc = _("Netvisor: export employee '%s'", record.name)
                netvisor_model.with_delay(
                    description=job_desc
                ).netvisor_export_employee(record, effective_company_id)
            else:
                # Immediate sending
                netvisor_model.netvisor_export_employee(record, effective_company_id)
