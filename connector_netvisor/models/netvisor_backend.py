import logging
from odoo import api
from odoo import fields
from odoo import models
from odoo import _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.exceptions import Warning
from netvisor_api_client import Netvisor
from netvisor_api_client.exc import AuthenticationFailed

_logger = logging.getLogger(__name__)


class NetvisorBackend(models.Model):

    _name = "netvisor.backend"
    _inherit = ["connector.backend"]
    _description = "Backend for Netvisor integration"
    rec_name = "partner"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
        required=True,
    )

    active = fields.Boolean(
        default=True,
    )

    environment = fields.Selection(
        string="Environment",
        selection=[("test", "Test"), ("production", "Production")],
        default="test",
    )

    host = fields.Char(
        string="External host",
        default="https://isvapi.netvisor.fi",
    )

    sender = fields.Char(
        string="Client",
        default="Odoo",
        readonly=True,
    )

    partner = fields.Char(
        string="Partner ID",
        required=True,
    )

    partner_key = fields.Char(
        string="Partner Key",
        required=True,
    )

    customer = fields.Char(
        string="Customer ID",
        required=True,
    )

    customer_key = fields.Char(
        string="Customer Key",
        required=True,
    )

    language = fields.Selection(
        string="API language",
        selection=[("EN", "English"), ("FI", "Finnish"), ("SE", "Swedish")],
        required=True,
        default="EN",
    )

    @api.onchange("environment")
    def onchange_environment(self):
        for record in self:
            if record.environment == "production":
                record.host = "https://integration.netvisor.fi"
            else:
                record.host = "https://isvapi.netvisor.fi"

    def action_test_authentication(self):
        """
        Test authentication
        :return:
        """
        self.ensure_one()
        client = self.authenticate()

        try:
            # Try to list customers
            client.customers.list()
            # TODO: use something else than a warning popup
            raise Warning(_("Authentication successful"))
        except AuthenticationFailed as e:
            _logger.error(e)
            raise ValidationError(
                _("Authentication failed! Please see server log for more information")
            )

    def authenticate(self):
        """
        Start an API session
        :return: Netvisor client
        """
        if not self.company_id.company_registry:
            raise ValidationError(
                _("Company registry is missing. Please provide and try again")
            )

        client = Netvisor(
            host=self.host,
            sender=self.sender,
            partner_id=self.partner,
            partner_key=self.partner_key,
            customer_id=self.customer,
            customer_key=self.customer_key,
            organization_id=self.company_id.company_registry,
            language=self.language,
        )

        return client

    def action_import_customers(self):
        """
        Import customers from Netvisor
        :return:
        """
        _logger.debug(_("Importing customers from Netvisor"))
        netvisor_model = self.env["netvisor.partner"]

        for record in self:
            job_desc = _(
                "Netvisor: import customers for {}".format(record.company_id.name)
            )

            netvisor_model.with_delay(description=job_desc).netvisor_import_customers()

    def action_import_suppliers(self):
        """
        Import suppliers from Netvisor
        :return:
        """
        raise UserError("Importing suppliers not implemented.")

    def action_import_products(self):
        """
        Import products from Netvisor
        :return:
        """
        _logger.debug(_("Importing products from Netvisor"))
        netvisor_model = self.env["netvisor.product"]

        for record in self:
            job_desc = _(
                "Netvisor: import products for {}".format(record.company_id.name)
            )

            netvisor_model.with_delay(description=job_desc).netvisor_import_products()

    def action_export_products(self):
        """
        Export or update all products to Netvisor
        :return:
        """
        _logger.debug(_("Exporting products to Netvisor"))
        netvisor_model = self.env["netvisor.product"]

        for record in self:
            job_desc = _(
                "Netvisor: export products for {}".format(record.company_id.name)
            )

            netvisor_model.with_delay(description=job_desc).netvisor_export_products()

    def action_cron_update_invoices_status(self):
        """
        Scheduled update all invoices status
        """
        for backend in self.search([]):
            backend.action_update_invoices_status()

    def action_update_invoices_status(self):
        """
        Update status for all invoices
        """

        _logger.info(_("Updating invoice status from Netvisor"))
        netvisor_model = self.env["netvisor.invoice"]

        open_status = ["open", "overdue", "unsent"]

        bindings = netvisor_model.search(
            [
                ("state", "=", "posted"),
                ("odoo_id", "!=", False),
                ("netvisor_status", "in", open_status),
            ]
        )
        _logger.debug(_(f"Updating status for invoices: {bindings.ids}"))

        for binding in bindings:
            job_desc = _(f"Update status for invoice {binding.name}")

            binding.with_delay(description=job_desc).netvisor_import_status(
                binding.odoo_id
            )
