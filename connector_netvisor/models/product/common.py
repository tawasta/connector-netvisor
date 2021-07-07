from odoo import api
from odoo import fields
from odoo import models
from odoo import _


class NetvisorProduct(models.Model):
    """Binding Model for the Netvisor Product"""

    _name = "netvisor.product"
    _inherit = "netvisor.binding"
    _inherits = {"product.product": "odoo_id"}
    _description = "Netvisor Product"

    odoo_id = fields.Many2one(
        comodel_name="product.product",
        string="Odoo Product",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A Netvisor binding for this product already exists.",
        ),
    ]

    def netvisor_import_products(self):
        """
        Import all products from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend()
        client = backend.authenticate()
        records = client.products.list()

        for record in records:
            job_desc = _(
                "Netvisor: import product '{}'".format(record.get("product_code"))
            )
            self.with_delay(description=job_desc).netvisor_import_product(
                record.get("netvisor_key")
            )

    def netvisor_export_products(self):
        """
        Export all products to Netvisor
        :return:
        """
        records = self.env["product.product"].search([])

        for record in records:
            job_desc = _("Netvisor: export product '{}'".format(record.display_name))
            self.with_delay(description=job_desc).netvisor_export_product(record)

    def netvisor_import_product(self, netvisor_key):
        """
        Import a product from Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_product(backend, netvisor_key)

    def netvisor_export_product(self, record):
        """
        Export a product to Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_product(backend, record)


class Product(models.Model):
    _inherit = "product.product"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.product",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    def action_netvisor_export_record(self):
        netvisor_model = self.env["netvisor.product"]
        if len(self) == 1:
            # No delayed job
            netvisor_model.netvisor_export_product(self)
        else:
            for record in self:
                job_desc = _(
                    "Netvisor: export product '{}'".format(record.display_name)
                )
                netvisor_model.with_delay(description=job_desc).netvisor_export_product(
                    record
                )

    def write(self, values):
        res = super().write(values)
        for record in self:
            self._event("on_product_update").notify(record)

        return res

    @api.model
    def create(self, values):
        res = super().create(values)
        for record in self:
            self._event("on_product_update").notify(record)

        return res
