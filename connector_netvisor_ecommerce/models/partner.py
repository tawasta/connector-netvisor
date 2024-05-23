from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    company_email = fields.Char(string="Company email")
    use_transmit_method_snailmail = fields.Boolean(
        "Use snailmail (technical field)",
        default=False,
        copy=False,
    )

    def create_company(self):
        """
        Set invoicing email to company
        """
        res = super().create_company()

        vals = {}
        if self.email_invoicing_address:
            vals = {
                "email_invoicing_address": self.email_invoicing_address,
                "email": False,
            }

        elif hasattr(self, "company_email") and self.company_email:
            vals = {
                "email_invoicing_address": self.company_email,
                "email": False,
            }

        self.parent_id.write(vals)

        if self.parent_id.email_invoicing_address:
            # Remove invoicing address from contact
            self.email_invoicing_address = False

        return res
