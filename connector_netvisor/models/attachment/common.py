from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    datas_utf8 = fields.Char(
        string="Datas as UTF-8 string",
        compute="_compute_datas_utf8",
    )

    def _compute_datas_utf8(self):
        for record in self:
            record.datas_utf8 = record.datas.decode("utf-8")
