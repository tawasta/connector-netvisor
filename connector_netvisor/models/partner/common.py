from odoo import _, api, fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    name_extension = fields.Char(string="Name extension")
    email_invoicing_address = fields.Char(
        string="Invoicing email", help="Netvisor invoicing email"
    )

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.partner",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )

    def action_netvisor_export_record(self, use_queue=True, company_id=False):
        """
        Export partner to Netvisor
        :return:
        """
        for record in self:
            netvisor_model = self.env["netvisor.partner"]

            if not company_id and record.company_id:
                company_id = record.company_id.id
            elif not company_id:
                company_id = self.env.user.company_id.id

            if company_id:
                netvisor_model = netvisor_model.with_context(company_id=company_id)

            if use_queue:
                # Queued sending
                job_desc = _(
                    "Netvisor: export customer '{}'".format(record.display_name)
                )
                netvisor_model.with_delay(
                    description=job_desc
                ).netvisor_export_customer(record, company_id)
            else:
                # Immediate sending
                netvisor_model.netvisor_export_customer(record, company_id)

    def write(self, values):
        """
        Override to force partner create or update on each write
        :param values: values dict
        :return:
        """
        res = super().write(values)
        auto_export = self._get_auto_export(values)
        if auto_export and not self.env.context.get("skip_export"):
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
        auto_export = True
        if auto_export and not self.env.context.get("skip_export"):
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

    def _get_auto_export(self, values):
        """
        Decide if we want to auto-export partner(s)
        """
        auto_export = False

        # These fields will trigger the auto-export
        triggers = [
            "name",
            "street",
            "street2",
            "city",
            "state_id",
            "zip",
            "country_id",
            "vat",
            "business_code",
            "phone",
            "mobile",
            "email",
            "ref",
        ]

        if [i for i in values if i in triggers]:
            # If any fields match trigger fields
            auto_export = True

        return auto_export
