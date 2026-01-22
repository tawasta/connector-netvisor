import logging
from decimal import Decimal

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class NetvisorPayment(models.Model):
    """Binding Model for the Netvisor Payment"""

    _name = "netvisor.payment"
    _inherit = "netvisor.binding"
    _inherits = {"account.payment": "odoo_id"}
    _description = "Netvisor Payment"

    odoo_id = fields.Many2one(
        comodel_name="account.payment",
        string="Account payment",
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

    def netvisor_get_payment_by_name(self, name, company_id=False):
        """
        Get a payment by its name
        :param name: Payment name
        :return: Netvisor payment record or None
        """
        backend = self.get_netvisor_backend(company_id)
        endpoint = "salespaymentlist.nv"
        params = {
            "searchbyname": name,
        }

        records = backend._api_request_get(endpoint, params=params)
        return records

    def netvisor_import_payments(self, company_id=False):
        """
        Import all payments from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend(company_id)
        endpoint = "salespaymentlist.nv"

        params = {
            "lastmodifiedstart": backend.payments_start_date.isoformat(),
            "limitlinkedpayments": 1,
            "limitbytype": "excludecreditloss",
        }

        records = backend._api_request_get(endpoint, params=params)

        if backend.company_id:
            self = self.with_company(backend.company_id.id)

        count = len(records)

        for record in records:
            job_desc = _(
                "Netvisor: import payment for invoice '{}'".format(
                    record.get("InvoiceNumber").get("#text")
                )
            )

            # Convert decimals to floats. Generally this isn't a great idea,
            # but json.dumps() can't handle Decimals

            for k, v in record.items():
                if isinstance(record[k], Decimal):
                    record[k] = float(v)

            self.with_delay(description=job_desc).netvisor_import_payment(
                record, backend.company_id
            )

        backend.payments_start_date = fields.Datetime.now()
        return _(f"{count} payment import jobs done")

    def netvisor_import_payment(self, record, company_id=False):
        """
        Import a payment from Netvisor
        :param netvisor_key: Netvisor external ID
        :return:
        """
        backend = self.get_netvisor_backend(company_id)

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_payment(backend, record)

    def netvisor_export_payment(self, record, company=False):
        """
        Export a payment to Netvisor
        :param record: Payment record
        :param company: Company ID
        :return:
        """
        if not company and record.company_id:
            company = record.company_id.id

        backend = self.get_netvisor_backend(company)

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_payment(backend, record)
