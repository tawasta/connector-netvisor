import logging

from netvisor_api_client import Netvisor
from netvisor_api_client.exc import AuthenticationFailed

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

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
        required=True,
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

    # Print channel (invoice template)
    print_channel_format = fields.Char(
        string="Invoice print channel",
        help="You can set a custom invoice channel here (invoice template)."
        "Use '1' for default template",
        default=1,
        required=True,
    )

    print_channel_format_type = fields.Selection(
        string="Invoice print channel type",
        help="'netvisor' for default templates, 'customer' for customized templates",
        selection=[("netvisor", "Netvisor"), ("customer", "Customer")],
        default="netvisor",
        required=True,
    )

    # Invoicing settings
    auto_open_refunds = fields.Boolean(
        string="Set refunds as sent",
        help="When sending a refund invoice, mark it as sent (open)",
        default=False,
    )
    customer_invoice_allow_updating = fields.Boolean(
        string="Allow updating invoices",
        help="Allow updating invoice information from Odoo to Netvisor",
        default=False,
    )

    # Import / export settings
    customer_import_create = fields.Boolean(
        string="Create new customers on import",
        help="When importing customer that doesn't exist in Odoo, create a new partner",
        default=True,
    )
    customer_import_update = fields.Boolean(
        string="Update existing customers on import",
        help="When importing customer that exists in Odoo, update partner values",
        default=True,
    )

    product_import_create = fields.Boolean(
        string="Create new products on import",
        help="When importing products that doesn't exist in Odoo, create a new products",
        default=True,
    )
    product_import_update = fields.Boolean(
        string="Update existing products on import",
        help="When importing products that exists in Odoo, update product values",
        default=True,
    )

    # Sale invoice payments
    payments_start_date = fields.Date(
        string="Payments import start date",
        help="Starting date for payments import. "
        "Will be automatically updated after fetching payments",
        default="2020-01-01",
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
            # TODO: use something else than a error popup
            raise ValidationError(_("Authentication successful"))
        except AuthenticationFailed as e:
            _logger.error(e)
            raise ValidationError(_("Authentication failed!\n{}".format(e))) from e

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
            netvisor_model = netvisor_model.with_context(
                company_id=record.company_id.id
            )

            job_desc = _(
                "Netvisor: import customers for {}".format(record.company_id.name)
            )

            netvisor_model.with_delay(description=job_desc).netvisor_import_customers(
                record.company_id
            )

    def action_import_suppliers(self):
        """
        Import suppliers from Netvisor
        :return:
        """
        _logger.debug(_("Importing suppliers from Netvisor"))

        raise UserError(_("Importing suppliers not implemented."))

    def action_import_products(self):
        """
        Import products from Netvisor
        :return:
        """
        _logger.debug(_("Importing products from Netvisor"))
        netvisor_model = self.env["netvisor.product"]

        for record in self:
            netvisor_model = netvisor_model.with_context(
                company_id=record.company_id.id
            )

            job_desc = _(
                "Netvisor: import products for {}".format(record.company_id.name)
            )

            netvisor_model.with_delay(description=job_desc).netvisor_import_products(
                record.company_id
            )

    def action_export_products(self):
        """
        Export or update all products to Netvisor
        :return:
        """
        _logger.debug(_("Exporting products to Netvisor"))
        netvisor_model = self.env["netvisor.product"]

        for record in self:
            netvisor_model = netvisor_model.with_context(
                company_id=record.company_id.id
            )

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

        bindings = netvisor_model.search(
            [
                ("odoo_id", "!=", False),
                ("netvisor_status", "not in", ["paid", "rejected"]),
            ]
        )
        _logger.debug(_(f"Updating status for invoices: {bindings.ids}"))

        for binding in bindings:
            job_desc = _(f"Update status from Netvisor for invoice {binding.name}")

            binding.with_delay(description=job_desc).netvisor_import_status(
                binding.odoo_id
            )

    def action_cron_import_payments(self):
        """
        Scheduled import all new payments
        """
        for backend in self.search([]):
            backend.action_import_payments()

    def action_import_payments(self):
        """
        Import all new payments from Netvisor
        """

        netvisor_model = self.env["netvisor.payment"]

        job_desc = _("Import payments from Netvisor")
        _logger.info(job_desc)

        netvisor_model.with_delay(description=job_desc).netvisor_import_payments(
            self.company_id.id
        )
