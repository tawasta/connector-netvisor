import logging

from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)


class NetvisorPaymentExportMapper(Component):
    _name = "netvisor.payment.export.mapper"
    _description = "Netvisor Payment Export Mapper"
    _inherit = "base.export.mapper"
    _usage = "export.mapper"
    _apply_on = ["netvisor.payment"]

    def export_payment(self, backend, record):
        """
        Export a payment to Netvisor
        :param backend: Netvisor backend record
        :param record: Payment record
        :return:
        """
        # Force record company for property fields
        if record.company_id:
            record = record.with_company(record.company_id.id)
        binding_model = self.env["netvisor.payment"]

        msg_existing = _("Tried to export a payment that is already sent to Netvisor")
        # Check if payment is already exported
        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )
        if binding:
            record.message_post(
                body=msg_existing,
            )
            return msg_existing

        # Try to find existing payment from Netvisor
        existing_payment = binding_model.netvisor_get_payment_by_name(
            record.name, record.company_id
        )
        if existing_payment:
            try:
                binding_model.create(
                    {
                        "backend_id": backend.id,
                        "external_id": existing_payment[0].get("NetvisorKey"),
                        "odoo_id": record.id,
                    }
                )
            except IntegrityError:
                # Binding already exists
                pass
            
            record.message_post(
                body=msg_existing,
            )
            return msg_existing

        if record.payment_type == "inbound":
            template = "connector_netvisor.netvisor_sales_payment"
            endpoint = "salespayment.nv"
        else:
            template = "connector_netvisor.netvisor_payment"
            endpoint = "payment.nv"

        xml_string = self.env["ir.qweb"]._render(template, {"record": record})

        _logger.debug(xml_string)

        if not record.reconciled_invoice_ids and not record.payment_transaction_id:
            raise RetryableJobError(
                _("Payment has no reconciled invoice or payment transaction yet")
            )

        if False in record.reconciled_invoice_ids.mapped("netvisor_status"):
            raise RetryableJobError(_("Reconciled invoice is not yet sent to Netvisor"))

        msg = _("Payment %s sent to Netvisor", record._get_html_link())
        for invoice in record.reconciled_invoice_ids:
            if invoice.netvisor_delayed_send:
                invoice.netvisor_delayed_send = False

            if invoice.netvisor_status != "open":
                # Set invoice Netvisor status to "open"
                # to allow allocating a payment in Netvisor
                tmp_status = invoice.netvisor_status
                invoice.netvisor_status = "open"
                invoice.action_netvisor_export_status()

                # Set invoice Netvisor status back to original status
                # (usually "paid" here)
                invoice.netvisor_status = tmp_status

            invoice.message_post(body=msg)

        res = backend._api_request_post(endpoint, xml_string)

        if res:
            try:
                binding_model.create(
                    {
                        "backend_id": backend.id,
                        "external_id": res.get("InsertedDataIdentifier"),
                        "odoo_id": record.id,
                    }
                )
                record.mark_as_sent()
                record.message_post(body=msg)
            except IntegrityError:
                # Binding already exists
                pass

            msg = _(f"Created payment '{record.display_name}'")
        else:
            raise UserError(
                _(
                    "Something went wrong when exporting payment. "
                    "Please see log for more details"
                )
            )

        return msg
