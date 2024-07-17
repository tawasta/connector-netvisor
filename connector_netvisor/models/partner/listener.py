from odoo.addons.component.core import Component


class PartnerEventListener(Component):
    _name = "partner.event.listener"
    _inherit = "base.event.listener"

    def on_partner_update(self, record):
        """
        Export or update partner to Netvisor
        :param record: Partner record
        :return:
        """
        record.action_netvisor_export_record()
