from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    company_email = fields.Char(string="Company email")

    def create_company(self):
        """
        Set invoicing email to company
        """
        res = super().create_company()

        if hasattr(self, "company_email") and self.company_email:
            self.parent_id.email_invoicing_address = self.company_email

        return res
