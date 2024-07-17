import logging
from datetime import datetime

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class NetvisorPaymentImportMapper(Component):
    _name = "netvisor.payment.import.mapper"
    _description = "Netvisor Payment Import Mapper"
    _usage = "import.mapper"
    _inherit = "base.import.mapper"
    _apply_on = ["netvisor.payment"]

    def import_payment(self, backend, record):
        """
        Import or update a payment from Netvisor
        :param backend: Netvisor backend record
        :param record: Payment record
        :return:
        """
        netvisor_model = self.env["netvisor.payment"]

        payment_values = self.map_record(record).values()
        payment_values["company_id"] = backend.company_id.id

        netvisor_key = record.get("netvisor_key")

        # Search for existing binding
        existing_binding = netvisor_model.search(
            [
                ("external_id", "=", netvisor_key),
                ("backend_id", "=", backend.id),
            ],
            limit=1,
        )

        if existing_binding:
            # Updating payments is not implemented
            return _("Payment already imported. Nothing to do")

        # No existing binding
        binding_values = {"backend_id": backend.id, "external_id": netvisor_key}

        invoice_number = record.get("InvoiceNumber").get("#text")
        if not invoice_number:
            raise ValidationError(_("Payment doesn't include invoice number"))

        invoice = self.env["account.move"].search(
            [
                ("name", "=", invoice_number),
                ("company_id", "=", backend.company_id.id),
            ],
        )

        if not invoice:
            # If invoice is not found, assume it's created outside Odoo,
            # or has been deleted from Odoo, and doesn't need actions
            return _("Can't find an invoice to match the payment to")

        if len(invoice) != 1:
            raise ValidationError(_(f"Found more than one invoice {invoice_number}"))

        if invoice.payment_state == "paid":
            return _("Invoice is already fully paid. Nothing to do")

        if invoice.payment_state == "reversed":
            return _("Invoice is reversed. Nothing to do")

        # Payment register has slightly different field names
        # Let's copy the dict to leave original account.payment dict intact
        payment_register_values = payment_values.copy()
        payment_register_values["communication"] = payment_register_values.pop("ref")
        payment_register_values["payment_date"] = payment_register_values.pop("date")

        # noinspection PyProtectedMember
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(payment_register_values)
            ._create_payments()
        )

        binding_values["odoo_id"] = payment.id
        netvisor_model.create(binding_values)

        return _(f"Created payment '{payment.id}'")

    # Netvisor, Odoo
    direct = [
        ("ReferenceNumber", "ref"),
    ]

    @mapping
    def amount(self, record):
        amount = record.get("Sum").replace(",", ".")

        res = {"amount": amount}

        return res

    @mapping
    def date(self, record):
        date = datetime.strptime(record.get("Date"), "%d.%m.%Y")

        res = {"date": date}

        return res

    @mapping
    def payment_method_id(self, record):
        # This will currently fetch the first appicable method
        payment_method = self.env["account.payment.method"].search(
            [("payment_type", "=", "inbound")], limit=1
        )

        res = {"payment_method_id": payment_method.id}

        return res

    @mapping
    def group_payment(self, record):
        res = {"group_payment": True}

        return res

    @mapping
    def payment_difference_handling(self, record):
        res = {"payment_difference_handling": "open"}

        return res
