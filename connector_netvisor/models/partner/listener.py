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

        # Auto-update is disabled for now
        # It can be added to settings later if needed
        # Auto-updating partners on every update causes a lot of unnecessary exports
        auto_update = False
        if auto_update:
            record.action_netvisor_export_record()