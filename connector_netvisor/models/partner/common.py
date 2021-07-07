from odoo import api
from odoo import fields
from odoo import models
from odoo import _


class NetvisorPartner(models.Model):
    """Binding Model for the Netvisor Partner"""

    _name = "netvisor.partner"
    _inherit = "netvisor.binding"
    _inherits = {"res.partner": "odoo_id"}
    _description = "Netvisor Partner"

    odoo_id = fields.Many2one(
        comodel_name="res.partner",
        string="Odoo Partner",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A Netvisor binding for this partner already exists.",
        ),
    ]

    def netvisor_import_customers(self):
        """
        Import all customers from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend()
        client = backend.authenticate()
        records = client.customers.list()

        for record in records:
            job_desc = _("Netvisor: import customer '{}'".format(record.get("name")))
            self.with_delay(description=job_desc).netvisor_import_customer(
                record.get("netvisor_key")
            )

    def netvisor_import_customer(self, netvisor_key):
        """
        Import a partner from Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_customer(backend, netvisor_key)

    def netvisor_export_customer(self, record):
        """
        Export a partner to Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_customer(backend, record)


class Partner(models.Model):
    _inherit = "res.partner"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.partner",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    def action_netvisor_export_record(self):
        netvisor_model = self.env["netvisor.partner"]
        for record in self:
            job_desc = _("Netvisor: export customer '{}'".format(record.display_name))
            netvisor_model.with_delay(description=job_desc).netvisor_export_customer(
                record
            )

    def write(self, values):
        res = super().write(values)
        for record in self:
            self._event("on_partner_update").notify(record)

        return res

    @api.model
    def create(self, values):
        res = super().create(values)
        for record in self:
            self._event("on_partner_update").notify(record)

        return res

    def get_combined_street(self):
        """
        :return: Combined line of street and street2
        """
        self.ensure_one()
        if self.street and self.street2:
            street = f"{self.street} {self.street2}"
        else:
            street = self.street or ""

        return street
