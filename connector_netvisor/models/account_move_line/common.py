import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Creating bindings for each line seems kind of unnecessary
    netvisor_key = fields.Integer("Netvisor key")
