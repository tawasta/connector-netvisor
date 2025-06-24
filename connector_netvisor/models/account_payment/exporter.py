from psycopg2 import IntegrityError

from odoo import _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.queue_job.exception import RetryableJobError


from odoo.addons.component.core import Component

import logging

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

        binding = binding_model.search(
            [("odoo_id", "=", record.id), ("backend_id", "=", backend.id)]
        )

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

        if binding:
            return _("This payment is already sent to Netvisor")
        else:
            # Export paid invoice status to allow allocating a payment in Netvisor
            for invoice in record.reconciled_invoice_ids:
                invoice.write(
                    {"netvisor_status": "open", "netvisor_delayed_send": False}
                )
                invoice.action_netvisor_export_status()

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
                except IntegrityError:
                    # Binding already exists
                    pass

                msg = _("Created payment '{}'".format(record.display_name))

                # Update invoice status
                for invoice in record.reconciled_invoice_ids:
                    job_desc = _(
                        "Update '{}' status from Netvisor)".format(invoice.name)
                    )
                    invoice.with_delay(
                        description=job_desc
                    ).action_netvisor_import_status()

            else:
                raise UserError(
                    _(
                        "Something went wrong when exporting payment. "
                        "Please see log for more details"
                    )
                )

        return msg
