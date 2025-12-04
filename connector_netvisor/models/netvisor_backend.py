import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timedelta

import httpx
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
        selection=[
            ("test", "Test"),
            ("production", "Production"),
            ("disabled", "Disabled"),
        ],
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

    # Customer invoice settings
    auto_open_refunds = fields.Boolean(
        string="Set refunds as sent",
        help="When sending a refund invoice, mark it as sent (open)",
        default=False,
    )
    customer_invoice_allow_updating = fields.Boolean(
        string="Allow updating customer invoices",
        help="Allow updating customer invoice information from Odoo to Netvisor",
        default=False,
    )
    customer_invoice_use_delivery_address = fields.Boolean(
        string="Use delivery address",
        help="Send customer invoice delivery address to Netvisor",
        default=True,
    )
    customer_invoice_use_product_code = fields.Boolean(
        string="Use product code",
        help="Send product code on invoice lines",
        default=True,
    )
    customer_invoice_use_product_name = fields.Boolean(
        string="Use product name",
        help="Send product name on invoice lines",
        default=True,
    )
    customer_invoice_our_reference = fields.Selection(
        string="Our reference",
        help="The field used as our reference",
        selection=[
            ("ref", "Customer reference"),
            ("invoice_origin", "Invoice origin"),
        ],
        default="ref",
    )
    customer_invoice_your_reference = fields.Selection(
        string="Your reference",
        help="The field used as your reference",
        selection=[
            ("ref", "Customer reference"),
            ("invoice_origin", "Invoice origin"),
        ],
        default=False,
    )
    customer_invoice_send_order_reference = fields.Boolean(
        string="Send order reference",
        help="Send order reference to Netvisor",
        default=True,
    )
    customer_invoice_override_total_amount = fields.Boolean(
        string="Override total amount",
        help="If this is selected, Netvisor will not calculate the total amount from invoice rows",
        default=False,
    )
    customer_invoice_writeoff_account_id = fields.Many2one(
        string="Writeoff account",
        help="Use this account when making credit loss payments",
        comodel_name="account.account",
    )

    # Purchase invoice settings
    purchases_start_date = fields.Datetime(
        string="Import start date",
        help="When fetching the purchase invoices, use this date as the "
        "lower boundary for the invoice date. This field gets "
        "automatically updated after a successful fetch.",
        default="2020-01-01 00:00:00",
    )
    purchase_invoice_allow_updating = fields.Boolean(
        string="Allow updating purchase invoices",
        help="Allow updating purchase invoice posting data from Odoo to Netvisor",
        default=False,
    )

    # Customer settings
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

    # Supplier settings
    supplier_import_start_date = fields.Date(
        string="Supplier import start date",
        help="Starting date for supplier import. "
        "Will be automatically updated after fetching suppliers",
        default="1970-01-01",
    )
    supplier_import_create = fields.Boolean(
        string="Create new suppliers on import",
        help="When importing supplier that doesn't exist in Odoo, create a new partner",
        default=True,
    )
    supplier_import_update = fields.Boolean(
        string="Update existing suppliers on import",
        help="When importing supplier that exists in Odoo, update partner values",
        default=True,
    )

    # Product settings
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

        # Try to list products
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
        Helper for httpx.post method

        :param endpoint: API Endpoint
        :param values: Requests data
        :param params: Requests params
        :return: Parser response dict
        """

        _logger.debug(_(f"Making a POST request to endpoint {endpoint}"))
        _logger.debug(values)

        if self.environment == "disabled":
            _logger.warning(_("Integration disabled. Not making the request"))
            return {"error": "Integration is disabled"}

        if params is None:
            params = {}

        url = self._get_request_url(endpoint, params)
        headers = self._get_authentication_headers(url)

        response = httpx.post(
            url=url,
            data=values,
            headers=headers,
            timeout=10,
        )

        res = self._parse_response(response)

        return res

    def _api_request_get(self, endpoint, params=None):
        """
        Helper for httpx.get method

        :param endpoint: API Endpoint
        :param params: Requests params
        :return: Parser response dict
        """
        _logger.debug(_(f"Making a GET request to endpoint {endpoint}"))

        if self.environment == "disabled":
            _logger.warning(_("Integration disabled. Not making the request"))
            return {"error": "Integration is disabled"}

        if params is None:
            params = {}

        url = self._get_request_url(endpoint, params)
        headers = self._get_authentication_headers(url)

        response = httpx.get(
            url=url,
            headers=headers,
        )

        res = self._parse_response(response)

        return res

    def _get_mac(self, url, timestamp_unix, timestamp_ansi, transaction_id):
        parameters = [
            url,
            self.sender,
            self.customer,
            timestamp_ansi,
            self.language,
            self.company_id.company_registry,
            transaction_id,
            timestamp_unix,
            self.customer_key,
            self.partner_key,
        ]
        joined_parameters = b"&".join(
            p.encode("utf-8") if isinstance(p, str) else p for p in parameters
        )

        # encode the string to ISO-8859-1 and perform the sha256-hash
        key = self.customer_key + "&" + self.partner_key
        h_mac = hmac.new(
            bytes(key, "ISO-8859-1"), joined_parameters, hashlib.sha256
        ).hexdigest()

        return h_mac

    def _get_authentication_headers(self, url):
        if not self.company_id.company_registry:
            raise ValidationError(
                _("Company registry is missing. Please provide and try again")
            )

        timestamp = datetime.now()
        # ANSI-format, e.g. "2025-01-01 00:00:00.000"
        timestamp_ansi = timestamp.isoformat(" ")[:-3]
        # UNIX timestamp without seconds, e.g. "1744635366"
        timestamp_unix = str(int(timestamp.timestamp()))

        transaction_id = uuid.uuid4().hex
        mac = self._get_mac(url, timestamp_unix, timestamp_ansi, transaction_id)

        headers = {
            "Content-type": "text/plain",
            "X-Netvisor-Authentication-Sender": self.sender,
            "X-Netvisor-Authentication-CustomerId": self.customer,
            "X-Netvisor-Authentication-PartnerId": self.partner,
            "X-Netvisor-Authentication-TimestampUnix": timestamp_unix,
            "X-Netvisor-Authentication-Timestamp": timestamp_ansi,
            "X-Netvisor-Interface-Language": self.language,
            "X-Netvisor-Organisation-ID": self.company_id.company_registry,
            "X-Netvisor-Authentication-TransactionId": transaction_id,
            "X-Netvisor-Authentication-MAC": mac,
            "X-Netvisor-Authentication-MACHashCalculationAlgorithm": "HMACSHA256",
            "X-Netvisor-Authentication-UseHTTPResponseStatusCodes": "1",
        }

        return headers

    def _get_request_url(self, endpoint, params):
        url = f"{self.host}/{endpoint}"
        if params:
            query_string = "&".join(f"{key}={value}" for key, value in params.items())
            url = f"{url}?{query_string}"

        return url

    def _parse_response(self, response):
        text = xmltodict.parse(response.text)
        headers = response.headers
        root = text.get("Root") or {}

        if not root:
            _logger.warning(f"Root element not found: {text}")

        status_code = response.status_code

        if status_code == 404:
            raise ValidationError(_("This endpoint doesn't seem to exist."))

        try:
            response_status = root.get("ResponseStatus") or {}
        except AttributeError as e:
            raise Exception(f"Error while trying to parse response '{root}': '{e}'")

        response_status_list = response_status.get("Status")

        _logger.debug(headers)
        _logger.debug(root.keys())
        _logger.debug(response_status)

        if response_status_list and response_status_list[0] == "FAILED":
            raise ValidationError(response_status_list[1])

        # TODO: smarter response handling
        if root.get("Replies"):
            res = root.get("Replies")
        elif "Customerlist" in root:
            res = root.get("Customerlist") and root["Customerlist"].get("Customer")
            if isinstance(res, dict):
                # Always put customers in a list
                res = [res]
        elif "Customer" in root:
            res = root.get("Customer", {})
        elif "Vendors" in root:
            res = root.get("Vendors") and root["Vendors"].get("Vendor", {})
            if isinstance(res, dict):
                # Always put vendors in a list
                res = [res]
        elif "Vendor" in root:
            res = root.get("Vendor", {})
        elif "DimensionNameList" in root:
            res = root.get("DimensionNameList") and root["DimensionNameList"].get(
                "DimensionName", {}
            )
            if isinstance(res, dict):
                # Always put dimensions in a list
                res = [res]
        elif "Product" in root:
            res = root.get("Product", {})
        elif "ProductList" in root:
            res = root.get("ProductList") and root["ProductList"].get("Product", {})
            if isinstance(res, dict):
                # Always put products in a list
                res = [res]
        elif "SalesInvoice" in root:
            res = root.get("SalesInvoice", {})
        elif "SalesPaymentList" in root:
            res = root.get("SalesPaymentList") and root["SalesPaymentList"].get(
                "SalesPayment", {}
            )
            if isinstance(res, dict):
                # Always put payments in a list
                res = [res]
        elif "PurchaseInvoice" in root:
            res = root.get("PurchaseInvoice", {})
        elif "PurchaseInvoiceList" in root:
            res = root.get("PurchaseInvoiceList") and root["PurchaseInvoiceList"].get(
                "PurchaseInvoice", {}
            )
            if isinstance(res, dict):
                # Always put invoices in a list
                res = [res]
        elif "PayrollRatios" in root:
            res = root.get("PayrollRatios", {})
            if isinstance(res, dict):
                # Always put ratios in a list
                res = [res]
        elif root.keys() and len(root.keys()) == 1:
            # Some endpoints just return the ResponseStatus
            res = {}
        else:
            _logger.error(root)
            raise ValidationError(_("Netvisor API response could not be parsed!"))

        if res is None:
            # Return iterable response
            res = {}

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

            job_desc = _(f"Netvisor: import customers for {record.company_id.name}")

            netvisor_model.with_delay(description=job_desc).netvisor_import_customers(
                record.company_id
            )

    def action_import_suppliers(self):
        """
        Import suppliers from Netvisor
        :return:
        """
        _logger.debug(_("Importing suppliers from Netvisor"))

        netvisor_model = self.env["netvisor.partner"]

        for record in self:
            netvisor_model = netvisor_model.with_context(
                company_id=record.company_id.id
            )

            job_desc = _(f"Netvisor: import suppliers for {record.company_id.name}")

            netvisor_model.with_delay(description=job_desc).netvisor_import_suppliers(
                record.company_id
            )

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

            job_desc = _(f"Netvisor: import products for {record.company_id.name}")

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

            job_desc = _(f"Netvisor: export products for {record.company_id.name}")

            netvisor_model.with_delay(description=job_desc).netvisor_export_products()

    def action_import_purchase_invoices(self):
        """
        Import purchase invoices from Netvisor
        :return:
        """
        _logger.debug(_("Importing purchase invoices from Netvisor"))
        netvisor_model = self.env["netvisor.invoice"]

        for record in self:
            netvisor_model = netvisor_model.with_context(
                company_id=record.company_id.id
            )

            job_desc = _(
                f"Netvisor: import purchase invoices for {record.company_id.name}"
            )

            netvisor_model.with_delay(
                description=job_desc
            ).netvisor_import_purchase_invoices(record.company_id)

            # Always fetch a week backwards, if new invoices have been created to past
            record.purchases_start_date = fields.Datetime.now() - timedelta(days=7)

    def _cron_import_purchase_invoices(self):
        for backend in self.search([]):
            backend.action_import_purchase_invoices()

    def _cron_update_invoices_status(self):
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

    def _cron_import_payments(self):
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

    def action_import_dimensions(self):
        """
        Import dimensions from Netvisor
        :return:
        """
        _logger.debug(_("Importing dimensions from Netvisor"))
        netvisor_model = self.env["netvisor.dimension"]

        for record in self:
            job_desc = _(f"Netvisor: import dimensions for {record.company_id.name}")

            netvisor_model.with_delay(description=job_desc).netvisor_import_dimensions()

    def _cron_import_dimensions(self):
        for backend in self.search([]):
            backend.action_import_dimensions()
