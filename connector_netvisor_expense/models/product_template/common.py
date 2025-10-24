from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    netvisor_expense_type = fields.Selection(
        selection=[
            ("custom", "Custom expenses"),
            ("travel", "Travel expenses"),
            ("daily", "Daily compensation"),
        ],
        name="Netvisor expense type",
    )

    netvisor_compensation_type = fields.Selection(
        selection=[
            ("domesticfull", "Domestic full"),
            ("domestichalf", "Domestic half"),
            ("foreign", "Foreign"),
        ],
        name="Netvisor compensation type",
    )

    netvisor_travel_type = fields.Selection(
        selection=[
            ("car", "Car"),
            ("car_with_trailer", "Car towing a trailer"),
            ("car_with_caravan", "Car towing a caravan"),
            ("car_with_heavy_cargo", "Car towing a heavy load"),
            ("car_with_big_machinery", "Car with heavy or large machinery"),
            ("car_with_dog", "Car with dog in the car"),
            ("car_travel_in_rough_terrain", "Car in difficult terrain"),
            ("motorboat_max_50hp", "Motorboat, up to 50 hp"),
            ("motorboat_over_50hp", "Motorboat, more than 50 hp"),
            ("snowmobile", "Snowmobile"),
            ("atv", "Quadbike (ATV)"),
            ("motorbike", "Motorcycle"),
            ("moped", "Moped"),
            ("other", "Other means of transport"),
            ("carbenefit", "Company car limited benefit"),
        ],
        name="Netvisor travel type",
    )
