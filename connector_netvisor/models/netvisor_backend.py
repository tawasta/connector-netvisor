import hashlib
import logging
import urllib.parse
import uuid
from datetime import datetime

import requests
import xmltodict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class NetvisorBackend(models.Model):

    _name = "netvisor.backend"
    _inherit = ["connector.backend"]
    _description = "Backend for Netvisor integration"
    rec_name = "partner"

    # region Fields
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
    # endregion

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

        # Try to list customers
        endpoint = "productlist.nv"
        self._api_request_get(endpoint)

        title = _("Authentication successful!")
        message = _("Everything seems properly set up.")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "sticky": False,
            },
        }

    def _api_request_post(self, endpoint, values, params=None):
        """
        Helper for requests.post method

        :param endpoint: API Endpoint
        :param values: Requests data
        :param params: Requests params
        :return: Parser response dict
        """
        _logger.debug(_("Making a POST request to endpoint {}".format(endpoint)))
        if params is None:
            params = {}

        url = self._get_request_url(endpoint, params)
        headers = self._get_authentication_headers(url)

        response = requests.post(
            url=url,
            data=values,
            headers=headers,
        )

        res = self._parse_response(response)

        return res

    def _api_request_get(self, endpoint, params=None):
        """
        Helper for requests.get method

        :param endpoint: API Endpoint
        :param params: Requests params
        :return: Parser response dict
        """
        _logger.debug(_("Making a GET request to endpoint {}".format(endpoint)))
        if params is None:
            params = {}

        url = self._get_request_url(endpoint, params)
        headers = self._get_authentication_headers(url)

        response = requests.get(
            url=url,
            headers=headers,
        )

        res = self._parse_response(response)

        return res

    def _get_mac(self, url, timestamp, transaction_id):
        parameters = [
            url,
            self.sender,
            self.customer,
            timestamp,
            self.language,
            self.company_id.company_registry,
            transaction_id,
            self.customer_key,
            self.partner_key,
        ]
        joined_parameters = b"&".join(
            p.encode("utf-8") if isinstance(p, str) else p for p in parameters
        )
        # SHA256 is used in documentation, but doesn't seem to be working
        # return hashlib.sha256(joined_parameters).hexdigest()
        return hashlib.md5(joined_parameters).hexdigest()

    def _get_authentication_headers(self, url):
        if not self.company_id.company_registry:
            raise ValidationError(
                _("Company registry is missing. Please provide and try again")
            )

        timestamp = datetime.now().isoformat(" ")[:-3]
        transaction_id = uuid.uuid4().hex
        mac = self._get_mac(url, timestamp, transaction_id)

        headers = {
            "Content-type": "text/plain",
            "X-Netvisor-Authentication-Sender": self.sender,
            "X-Netvisor-Authentication-CustomerId": self.customer,
            "X-Netvisor-Authentication-PartnerId": self.partner,
            "X-Netvisor-Authentication-Timestamp": timestamp,
            "X-Netvisor-Interface-Language": self.language,
            "X-Netvisor-Organisation-ID": self.company_id.company_registry,
            "X-Netvisor-Authentication-TransactionId": transaction_id,
            "X-Netvisor-Authentication-MAC": mac,
        }

        return headers

    def _get_request_url(self, endpoint, params):
        url = f"{self.host}/{endpoint}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        return url

    def _parse_response(self, response):
        text = xmltodict.parse(response.text)
        root = text.get("Root")

        status_code = response.status_code

        if status_code == 404:
            raise ValidationError(_("This endpoint doesn't seem to exist."))

        response_status = root.get("ResponseStatus")
        response_status_list = response_status.get("Status")

        _logger.debug(root.keys())
        _logger.debug(response_status)

        if response_status_list and response_status_list[0] == "FAILED":
            raise ValidationError(response_status_list[1])

        if root.get("Replies"):
            res = root.get("Replies")
        elif root.get("Customerlist"):
            res = root.get("Customerlist")
        elif root.get("Customer"):
            res = root.get("Customer")
        elif root.get("Product"):
            res = root.get("Product")
        elif root.get("ProductList"):
            res = root.get("ProductList").get("Product")
        elif root.get("SalesInvoice"):
            res = root.get("SalesInvoice")
        elif root.get("SalesPaymentList"):
            res = root.get("SalesPaymentList").get("SalesPayment")
        elif root.keys() and len(root.keys()) == 1:
            # Some endpoints just return the ResponseStatus
            res = {}
        else:
            raise ValidationError(_("Netvisor API response could not be parsed!"))

        return res

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
