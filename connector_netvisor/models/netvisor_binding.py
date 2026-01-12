from odoo import _, fields, models
from odoo.exceptions import UserError


class NetvisorBinding(models.AbstractModel):
    _name = "netvisor.binding"
    _description = "Netvisor Binding"
    _inherit = "external.binding"

    backend_id = fields.Many2one(
        comodel_name="netvisor.backend",
        string="Netvisor Backend",
        required=True,
        ondelete="restrict",
    )
    external_id = fields.Integer(
        "Netvisor ID",
        help="Netvisor record id",
        index=True,
    )
    netvisor_raw_content = fields.Text(
        "Raw Netvisor Content",
        help="Raw Netvisor response for debugging purposes",
    )

    def get_netvisor_backend(self, company=False):
        """
        Return Netvisor backend record based on the current user company
        :param company: Company record
        :return: Netvisor backend recordF
        """
        NetvisorBackend = self.sudo().env["netvisor.backend"]
        if not company and hasattr(self, "company_id"):
            # Use company set on record
            company = self.company_id

        if not company:
            # Use users company
            company = self.env.user.company_id

        if isinstance(company, int):
            company_id = company
        else:
            company_id = company.id

        backend = NetvisorBackend.search(
            [
                ("company_id", "=", company_id),
            ]
        )

        if not backend:
            raise UserError(
                _("Please configure a Netvisor backend for company {}.").format(
                    isinstance(company, int) and company or company.name
                )
            )

        return backend

    def get_netvisor_binding(self, backend_id, external_id):
        """
        Return Netvisor binding if one exists
        :param backend_id: Netvisor backend id
        :param external_id: Netvisor external id (Netvisor key)
        :return: Binding record
        """

        netvisor_model = self.env[self._name]

        res = netvisor_model.search(
            [
                ("external_id", "=", external_id),
                ("backend_id", "=", backend_id),
            ],
            limit=1,
        )

        return res
