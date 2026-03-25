from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def get_social_security_number(self):
        """
        Override the method to get the social security number from the employee's
        related partner instead of the employee itself.
        """
        res = super().get_social_security_number()
        partner = self.user_id.partner_id
        encrypted_ssn = partner.encrypted_social_security_number
        if not res and encrypted_ssn:
            encryption_key = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("social_security_number_encryption_key", default="")
                .strip()
            )
            res = partner.decrypt_social_security_number(encrypted_ssn, encryption_key)

        return res
