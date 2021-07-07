from odoo import SUPERUSER_ID, api


def init_netvisor_data(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["account.tax"]._init_netvisor_codes()
