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
                "Netvisor: import product '{}'".format(
                    record.get("product_code") or record.get("name")
                )
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
        :param netvisor_key: Netvisor external ID
        :return:
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_product(backend, netvisor_key)

    def netvisor_export_product(self, record):
        """
        Export a product to Netvisor
        :param record: Product record
        :return:
        """
        backend = self.get_netvisor_backend(record.company_id)

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
        """
        Export product(s) to Netvisor
        :return:
        """
        for record in self:
            netvisor_model = self.env["netvisor.product"]
            if record.company_id:
                netvisor_model = netvisor_model.with_context(
                    company_id=record.company_id.id
                )

            job_desc = _("Netvisor: export product '{}'".format(record.display_name))
            netvisor_model.with_delay(description=job_desc).netvisor_export_product(
                record
            )

    def write(self, values):
        """
        Override to force product create or update on each write
        :param values: values dict
        :return:
        """
        res = super().write(values)
        if not self.env.context.get("skip_export"):
            for record in self:
                self._event("on_product_update").notify(record)

        return res

    @api.model
    def create(self, values):
        """
        Override to force product export on each create
        :param values: values dict
        :return:
        """
        res = super().create(values)

        if not self.env.context.get("skip_export"):
            self._event("on_product_update").notify(res)

        return res
