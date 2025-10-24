import logging
from datetime import date
from odoo import _
from odoo import models

_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    def _prepare_account_move(self, line_ids):
        res = super()._prepare_account_move(line_ids)

        # Always use delayed send to prevent problems in subscription state,
        # if an error happens
        res["netvisor_delayed_send"] = True

        return res
