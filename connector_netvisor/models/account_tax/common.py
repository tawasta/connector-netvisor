from odoo import fields
from odoo import models

_TAX_MAPPING = {
    # l10n_fi
    # KOMY = Kotimaan Myynti, Domestic sales
    "l10n_fi.1_tax_dom_sales_goods_24": "KOMY",
    "l10n_fi.1_tax_dom_sales_goods_14": "KOMY",
    "l10n_fi.1_tax_dom_sales_goods_10": "KOMY",
    "l10n_fi.1_tax_dom_sales_goods_0": "KOMY",
    "l10n_fi.1_tax_dom_sales_service_24": "KOMY",
    "l10n_fi.1_tax_dom_sales_service_14": "KOMY",
    "l10n_fi.1_tax_dom_sales_service_10": "KOMY",
    # KOOS = Kotimaan Osto, Domestic purchase
    "l10n_fi.1_tax_dom_purchase_goods_24": "KOOS",
    "l10n_fi.1_tax_dom_purchase_goods_14": "KOOS",
    "l10n_fi.1_tax_dom_purchase_goods_10": "KOOS",
    "l10n_fi.1_tax_dom_purchase_service_24": "KOOS",
    "l10n_fi.1_tax_dom_purchase_service_14": "KOOS",
    "l10n_fi.1_tax_dom_purchase_service_10": "KOOS",
    "l10n_fi.1_tax_dom_purchase_brutto_24": "KOOS",
    "l10n_fi.1_tax_dom_purchase_brutto_14": "KOOS",
    "l10n_fi.1_tax_dom_purchase_brutto_10": "KOOS",
    "l10n_fi.1_tax_dom_purchase_0": "KOOS",
    # EUMY = EU-myynti, EU sales
    "l10n_fi.1_tax_eu_sales_goods_0": "EUMY",
    "l10n_fi.1_tax_eu_sales_service_0": "EUMY",
    # EUOS = EU-osot, EU purchase
    "l10n_fi.1_tax_eu_purchase_goods_24": "EUOS",
    "l10n_fi.1_tax_eu_purchase_goods_14": "EUOS",
    "l10n_fi.1_tax_eu_purchase_goods_10": "EUOS",
    "l10n_fi.1_tax_eu_purchase_service_24": "EUOS",
    "l10n_fi.1_tax_eu_purchase_service_14": "EUOS",
    "l10n_fi.1_tax_eu_purchase_service_10": "EUOS",
    # TODO: map the rest of the taxes
    "l10n_fi.1_vat0triangulation": "-",
    "l10n_fi.1_triangulation_purchase": "-",
    "l10n_fi.1_tax_construct_sales_0": "-",
    "l10n_fi.1_tax_construct_purchase_24": "-",
    "l10n_fi.1_tax_construct_purchase_24_finland": "-",
    "l10n_fi.1_aland_sales_0": "-",
    "l10n_fi.1_tax_non_eu_purchase_goods_24": "-",
    "l10n_fi.1_tax_non_eu_purchase_goods_14": "-",
    "l10n_fi.1_tax_non_eu_purchase_goods_10": "-",
    "l10n_fi.1_vat0export": "-",
    "l10n_fi.1_import_pay24": "-",
    "l10n_fi.1_import_deduct24": "-",
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

    def _init_netvisor_code(self):
        for tax_id in _TAX_MAPPING.keys():
            try:
                tax = self.env.ref(tax_id)
            except ValueError:
                continue

            if not tax.netvisor_code or tax.netvisor_code == "-":
                tax.netvisor_code = _TAX_MAPPING.get(tax_id)
