from odoo import api
from odoo import fields
from odoo import models
from odoo import _


class Partner(models.Model):
    _inherit = "res.partner"

    name_extension = fields.Char(string="Name extension")
    email_invoicing_address = fields.Char(string="Invoicing email")

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.partner",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    def action_netvisor_export_record(self):
        """
        Export partner to Netvisor
        :return:
        """
        for record in self:
            netvisor_model = self.env["netvisor.partner"]
            if record.company_id:
                netvisor_model = netvisor_model.with_context(
                    company_id=record.company_id.id
                )

            job_desc = _("Netvisor: export customer '{}'".format(record.display_name))
            netvisor_model.with_delay(description=job_desc).netvisor_export_customer(
                record
            )

    def write(self, values):
        """
        Override to force partner create or update on each write
        :param values: values dict
        :return:
        """
        res = super().write(values)
        if not self.env.context.get("skip_export"):
            for record in self:
                self._event("on_partner_update").notify(record)

        return res

    @api.model
    def create(self, values):
        """
        Override to force partner export on each create
        :param values: values dict
        :return:
        """
        res = super().create(values)
        if not self.env.context.get("skip_export"):
            self._event("on_partner_update").notify(res)

        return res

    def get_combined_street(self):
        """
        Get combined string for street and street2
        :return: String with streets
        """
        if not self:
            # If function is called without records
            return ""

        self.ensure_one()
        if self.street and self.street2:
            street = f"{self.street} {self.street2}"
        else:
            street = self.street or ""

        return street
