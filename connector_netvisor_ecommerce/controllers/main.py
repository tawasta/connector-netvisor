from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleNetvisor(WebsiteSale):
    def _checkout_form_save(self, mode, checkout, all_values):
        """
        Save company email to parent company
        """
        # Don't set email to company, use email_invoicing_address instead
        company_email = all_values.pop("company_email", "")
        checkout["email_invoicing_address"] = company_email
        all_values["email_invoicing_address"] = company_email

        transmit_method = checkout.get("customer_invoice_transmit_method_id")

        transmit_method_post_id = (
            request.env["transmit.method"].sudo().search([("code", "=", "post")])
        )
        transmit_method_email_id = (
            request.env["transmit.method"].sudo().search([("code", "=", "mail")])
        )

        if transmit_method and transmit_method == transmit_method_post_id:
            # Remove invoicing email if using post
            checkout["email_invoicing_address"] = False
            all_values["email_invoicing_address"] = False
        elif transmit_method and transmit_method == transmit_method_email_id:
            # Ensure that invoicing email is in values
            if not checkout.get("email_invoicing_address"):
                checkout["email_invoicing_address"] = all_values.get("email")

        res = super()._checkout_form_save(mode, checkout, all_values)

        return res
