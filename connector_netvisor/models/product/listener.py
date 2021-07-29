from odoo.addons.component.core import Component


class ProductEventListener(Component):
    _name = "product.event.listener"
    _inherit = "base.event.listener"

    def on_product_update(self, record):
        """
        Export or update product to Netvisor
        :param record: Partner record
        :return:
        """
        record.action_netvisor_export_record()
