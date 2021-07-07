from odoo.addons.component.core import Component


class PartnerEventListener(Component):
    _name = "partner.event.listener"
    _inherit = "base.event.listener"

    def on_partner_update(self, record):
        record.action_netvisor_export_record()
