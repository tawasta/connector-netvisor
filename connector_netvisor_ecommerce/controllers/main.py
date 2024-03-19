from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleNetvisor(WebsiteSale):
    def _checkout_form_save(self, mode, checkout, all_values):
        """
        Save company email to parent company
        """

        checkout["email_invoicing_address"] = all_values.get("company_email", "")

        res = super()._checkout_form_save(mode, checkout, all_values)

        return res
