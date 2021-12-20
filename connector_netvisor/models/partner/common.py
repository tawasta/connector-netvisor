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
        :param netvisor_key: Netvisor external ID
        :return:
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_customer(backend, netvisor_key)

    def netvisor_export_customer(self, record):
        """
        Export a partner to Netvisor
        :param record: Partner record
        :return:
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_customer(backend, record)


class Partner(models.Model):
    _inherit = "res.partner"

    name_extension = fields.Char(string="Name extension")

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
        netvisor_model = self.env["netvisor.partner"]
        for record in self:
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
