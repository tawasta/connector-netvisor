import datetime
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class NetvisorInvoice(models.Model):
    """Binding Model for the Netvisor Invoice"""

    _name = "netvisor.invoice"
    _inherit = "netvisor.binding"
    _inherits = {"account.move": "odoo_id"}
    _description = "Netvisor Invoice"

    odoo_id = fields.Many2one(
        comodel_name="account.move",
        string="Account move",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A Netvisor binding for this record already exists.",
        ),
    ]

    def netvisor_export_invoice(self, record):
        """
        Export an invoice to Netvisor
        """
        backend = self.get_netvisor_backend(record.company_id)
        _logger.debug(f"Exporting invoice {record.id} to Netvisor")

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_invoice(backend, record)

    def netvisor_import_purchase_invoices(self, company=False):
        """
        Import all products from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend(company)
        endpoint = "purchaseinvoicelist.nv"

        params = {
            # "lastmodifiedstart": backend.purchases_start_date.isoformat(),
            "begininvoicedate": backend.purchases_start_date.isoformat(),
            # "paymentstatus": "unpaid",
            # "invoicestatus": "open",
        }

        records = backend._api_request_get(endpoint, params=params)

        if backend.company_id:
            self = self.with_context(company_id=backend.company_id.id)

        for record in records:
            job_desc = _(
                "Netvisor: import purchase invoice '{}'".format(
                    record.get("NetvisorKey") or record.get("Name")
                )
            )
            self.with_delay(description=job_desc).netvisor_import_purchase_invoice(
                record.get("NetvisorKey"), backend.company_id
            )

    def netvisor_import_purchase_invoice(self, record, company_id=False):
        """
        Import a purchase invoice from Netvisor
        :param record: Purchase invoice record
        :return:
        """
        backend = self.get_netvisor_backend(company_id)

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_purchase_invoice(backend, record)

    def netvisor_import_status(self, record):
        """
        Update status from Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.update_status(record)

    def netvisor_import_invoice_details(self, record):
        """
        Get invoice details from Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.update_details(backend, record)

    def netvisor_export_status(self, record):
        """
        Update status to Netvisor
        """
        backend = self.get_netvisor_backend()

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.update_status(record)

    def netvisor_match_credit_note(self):
        """
        Match credit note in Netvisor
        """
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.match_credit_note(self)

    def action_update_invoice_status(self, invoice_status):
        """
        Update invoice status in Odoo
        :param invoice_status: The invoice status to update to
        :return:
        """
        for record in self:
            if record.netvisor_status == invoice_status:
                # Nothing to do
                return
            elif record.state == "cancel":
                # Cancelled invoices should not be opened by Netvisor, nothing to do
                pass
            elif invoice_status == "unsent":
                # Set to draft
                # Generally we don't want Netvisor to reset invoice to draft,
                # so this is disabled for now
                # record.odoo_id.button_draft()
                pass
            elif invoice_status in ["paid", "creditloss"]:
                if record.payment_state in ["paid", "reversed"]:
                    # Already paid, nothing to do
                    record.netvisor_status = invoice_status
                    return

                # Set invoice as fully paid
                # TODO: get correct payment date
                # TODO: get correct payment method
                # TODO: get correct journal

                # This will currently set today as payment date
                # It is usually incorrect, but we don't have the correct data here
                payment_date = datetime.date.today()

                payment_values = {
                    "group_payment": True,
                    "currency_id": record.currency_id.id,
                    "payment_date": payment_date,
                    "netvisor_send": False,
                }

                if invoice_status == "paid":
                    # Paid invoice
                    msg = _("Set invoice as paid (status from Netvisor)")

                    payment_values["amount"] = record.amount_residual
                    payment_values["payment_difference_handling"] = "open"
                else:
                    # Credit loss
                    msg = _("Set invoice as credit loss (status from Netvisor)")

                    payment_values["amount"] = 0
                    payment_values["payment_difference_handling"] = "reconcile"
                    payment_values["writeoff_label"] = _("Credit loss")
                    if record.netvisor_bind_ids:
                        payment_values[
                            "writeoff_account_id"
                        ] = record.netvisor_bind_ids[
                            0
                        ].backend_id.customer_invoice_writeoff_account_id.id

                _logger.debug(_("Payment values: {}".format(payment_values)))
                _logger.debug(_("Invoices to pay: {}".format(record.odoo_id.ids)))

                self.env["account.payment.register"].with_context(
                    active_model="account.move", active_ids=record.odoo_id.ids
                ).create(payment_values)._create_payments()

                record.odoo_id.message_post(body=msg)

            _logger.info(
                _("Updating record.name Netvisor status to {}").format(invoice_status)
            )
            record.netvisor_status = invoice_status
