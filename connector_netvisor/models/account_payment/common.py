import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    netvisor_bind_ids = fields.One2many(
        comodel_name="netvisor.payment",
        inverse_name="odoo_id",
        string="Netvisor Bindings",
    )
