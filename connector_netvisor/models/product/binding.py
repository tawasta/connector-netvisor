from odoo import _, fields, models


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
            "A Netvisor binding for this record already exists.",
        ),
    ]

    def netvisor_import_products(self, company=False):
        """
        Import all products from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend(company)
        client = backend.authenticate()
        records = client.products.list()

        if backend.company_id:
            self = self.with_context(company_id=backend.company_id.id)

        for record in records:
            job_desc = _(
                "Netvisor: import product '{}'".format(
                    record.get("product_code") or record.get("name")
                )
            )
            self.with_delay(description=job_desc).netvisor_import_product(
                record.get("netvisor_key"), backend.company_id
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

    def netvisor_import_product(self, netvisor_key, company=False):
        """
        Import a product from Netvisor
        :param netvisor_key: Netvisor external ID
        :return:
        """
        backend = self.get_netvisor_backend(company)

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
