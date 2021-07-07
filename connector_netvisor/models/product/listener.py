from odoo.addons.component.core import Component


class ProductEventListener(Component):
    _name = "product.event.listener"
    _inherit = "base.event.listener"

    def on_product_update(self, record):
        record.action_netvisor_export_record()
