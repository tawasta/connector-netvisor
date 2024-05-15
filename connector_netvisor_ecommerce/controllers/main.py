from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleNetvisor(WebsiteSale):
    def _checkout_form_save(self, mode, checkout, all_values):
        """
        Save company email to parent company
        """
        # Don't set email to company, use email_invoicing_address instead
        checkout["email_invoicing_address"] = checkout.pop("company_email", "")

        if all_values.get("use_transmit_method_snailmail"):
            # Remove invoicing email, if set
            checkout["email_invoicing_address"] = False
            # Set helper field as selected
            checkout["use_transmit_method_snailmail"] = True
            if hasattr(
                request.env["res.partner"], "customer_invoice_transmit_method_id"
            ):
                # Update transmit method
                transmit_method_id = (
                    request.env["transmit.method"]
                    .sudo()
                    .search([("code", "=", "post")])
                )
                checkout["customer_invoice_transmit_method_id"] = transmit_method_id.id
                all_values["customer_invoice_transmit_method_id"] = transmit_method_id.id
        else:
            # Set helper field as unselected
            checkout["use_transmit_method_snailmail"] = False
            # Ensure that invoicing email is in values
            checkout["email_invoicing_address"] = all_values.get("email")

        res = super()._checkout_form_save(mode, checkout, all_values)

        return res
