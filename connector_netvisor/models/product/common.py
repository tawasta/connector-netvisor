from odoo import _, api, fields, models


class Product(models.Model):
    _inherit = "product.product"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.product",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    def action_netvisor_export_record(self, use_queue=True, company_id=False):
        """
        Export product(s) to Netvisor
        :return:
        """
        for record in self:
            netvisor_model = self.env["netvisor.product"]

            if not company_id and record.company_id:
                company_id = record.company_id.id

            if company_id:
                netvisor_model = netvisor_model.with_context(company_id=company_id)

            if use_queue:
                # Queued sending
                job_desc = _(f"Netvisor: export product '{record.display_name}'")
                netvisor_model.with_delay(description=job_desc).netvisor_export_product(
                    record, company_id
                )
            else:
                # Immediate sending
                netvisor_model.netvisor_export_product(record, company_id)

    def action_netvisor_import_record(self, company_id=False):
        for record in self:
            netvisor_model = self.env["netvisor.product"]

            if not company_id and record.company_id:
                company_id = record.company_id.id

            if company_id:
                netvisor_model = netvisor_model.with_context(company_id=company_id)

            for binding in record.netvisor_bind_ids:
                netvisor_model.netvisor_import_product(binding.external_id, company_id)

    def write(self, values):
        """
        Override to force product create or update on each write
        :param values: values dict
        :return:
        """
        res = super().write(values)
        auto_export = False
        if auto_export and not self.env.context.get("skip_export"):
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

        auto_export = False
        if auto_export and not self.env.context.get("skip_export"):
            self._event("on_product_update").notify(res)

        return res
