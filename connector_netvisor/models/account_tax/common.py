from odoo import fields, models

_TAX_MAPPING = {
    # l10n_fi
    # KOMY = Kotimaan Myynti, Domestic sales
    "tax_dom_sales_goods_25_5": "KOMY",
    "tax_dom_sales_goods_24": "KOMY",
    "tax_dom_sales_goods_14": "KOMY",
    "tax_dom_sales_goods_10": "KOMY",
    "tax_dom_sales_goods_0": "KOMY",
    "tax_dom_sales_service_25_5": "KOMY",
    "tax_dom_sales_service_24": "KOMY",
    "tax_dom_sales_service_14": "KOMY",
    "tax_dom_sales_service_10": "KOMY",
    # KOOS = Kotimaan Osto, Domestic purchase
    "tax_dom_purchase_goods_25_5": "KOOS",
    "tax_dom_purchase_goods_24": "KOOS",
    "tax_dom_purchase_goods_14": "KOOS",
    "tax_dom_purchase_goods_10": "KOOS",
    "tax_dom_purchase_service_25_5": "KOOS",
    "tax_dom_purchase_service_24": "KOOS",
    "tax_dom_purchase_service_14": "KOOS",
    "tax_dom_purchase_service_10": "KOOS",
    "tax_dom_purchase_brutto_24": "KOOS",
    "tax_dom_purchase_brutto_14": "KOOS",
    "tax_dom_purchase_brutto_10": "KOOS",
    "tax_dom_purchase_0": "KOOS",
    # EUMY = EU-myynti, EU sales
    "tax_eu_sales_goods_0": "EUMY",
    "tax_eu_sales_service_0": "EUMY",
    # EUOS = EU-osot, EU purchase
    "tax_eu_purchase_goods_25_5": "EUOS",
    "tax_eu_purchase_goods_24": "EUOS",
    "tax_eu_purchase_goods_14": "EUOS",
    "tax_eu_purchase_goods_10": "EUOS",
    "tax_eu_purchase_service_25_5": "EUOS",
    "tax_eu_purchase_service_24": "EUOS",
    "tax_eu_purchase_service_14": "EUOS",
    "tax_eu_purchase_service_10": "EUOS",
    # TODO: map the rest of the taxes
    "vat0triangulation": "-",
    "triangulation_purchase": "-",
    "tax_construct_sales_0": "-",
    "tax_construct_purchase_25_5": "-",
    "tax_construct_purchase_24": "-",
    "tax_construct_purchase_25_5_finland": "-",
    "tax_construct_purchase_24_finland": "-",
    "aland_sales_0": "-",
    "tax_non_eu_purchase_goods_25_5": "-",
    "tax_non_eu_purchase_goods_24": "-",
    "tax_non_eu_purchase_goods_14": "-",
    "tax_non_eu_purchase_goods_10": "-",
    "vat0export": "-",
    "import_pay25_5": "-",
    "import_pay24": "-",
    "import_deduct25": "-",
    "import_deduct24": "-",
}


class AccountTax(models.Model):
    _inherit = "account.tax"

    netvisor_code = fields.Selection(
        string="Netvisor VAT code",
        selection=[
            ("-", "No VAT"),
            ("KOMY", "Domestic sales"),
            ("EUMY", "EU sales"),
            ("EUUM", "Sales outside the EU"),
            ("KOOS", "Domestic purchase"),
            ("EUOS", "EU purchase"),
            ("EUPO", "EU service purchase"),
            ("EUUO", "Non - EU purchases"),
            ("100%", "100% deductible tax"),
            ("EUPM312", "312 EU service sales"),
            ("EUPM309", "309 EU service sales"),
            ("EVTO", "Purchases of goods from other EU countries, non-deductible"),
            ("EVPO", "Purchases of services from other EU countries, non-deductible"),
            ("EVKV", "Non-deductible reverse charge"),
            ("KÄVE", "Reverse charge"),
            ("RAMY", "Sale of construction services"),
            ("RAOS", "Purchase of construction service"),
            ("EVRO", "Non-deductible purchase of construction service"),
            ("MAAL", "Non-EU imports VAT"),
            ("EVMA", "Non-EU imports VAT not deductible"),
        ],
        required=True,
        default="-",
    )

    def _init_netvisor_codes(self):
        """
        Set Netvisor tax codes for taxes in Odoo
        :return:
        """
        for tax in self.env["account.tax"].sudo().search([]):
            xml_id = tax.get_external_id()[tax.id]

            # Extract the template id from xml id
            # From "account.1_tax_dom_sales_goods_24"
            # To "tax_dom_sales_goods_24"
            dict_key = "_".join(xml_id.split("_")[1:])
            if dict_key in _TAX_MAPPING:
                tax.netvisor_code = _TAX_MAPPING.get(dict_key)
