from odoo import _, fields, models


class NetvisorPartner(models.Model):
    """Binding Model for the Netvisor Partner"""

    _name = "netvisor.partner"
    _inherit = "netvisor.binding"
    _inherits = {"res.partner": "odoo_id"}
    _description = "Netvisor Partner"

    odoo_id = fields.Many2one(
        comodel_name="res.partner",
        string="Odoo Partner",
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

    def netvisor_import_customers(self, company=False):
        """
        Import all customers from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend(company)
        endpoint = "customerlist.nv"
        customers = backend._api_request_get(endpoint)

        if backend.company_id:
            self = self.with_context(company_id=backend.company_id.id)

        for record in customers:
            job_desc = _("Netvisor: import customer '{}'".format(record.get("Name")))
            self.with_delay(description=job_desc).netvisor_import_customer(
                record.get("Netvisorkey"), backend.company_id
            )

    def netvisor_import_customer(self, netvisor_key, company=False):
        """
        Import a partner from Netvisor
        :param netvisor_key: Netvisor external ID
        :return:
        """
        backend = self.get_netvisor_backend(company)

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_customer(backend, netvisor_key)

    def netvisor_export_customer(self, record, company=False):
        """
        Export a partner to Netvisor
        :param record: Partner record
        :param company: Company ID
        :return:
        """
        backend = self.get_netvisor_backend(company)

        with backend.work_on(self._name) as work:
            exporter = work.component(usage="export.mapper")
            return exporter.export_customer(backend, record)

    def netvisor_import_suppliers(self, company=False):
        """
        Import all suppliers from Netvisor
        :return:
        """
        backend = self.get_netvisor_backend(company)
        endpoint = "getvendor.nv"
        params = {
            "changedsince": backend.supplier_import_start_date.isoformat(),
            "page": 1,  # TODO: handle pagination for over 500 vendors
        }
        suppliers = backend._api_request_get(endpoint, params=params)

        if backend.company_id:
            self = self.with_context(company_id=backend.company_id.id)

        for record in suppliers:
            job_desc = _(
                "Netvisor: import supplier '{}'".format(
                    record.get("VendorBaseInformation").get("Name")
                )
            )
            self.with_delay(description=job_desc).netvisor_import_supplier(
                record.get("NetvisorKey"), backend.company_id
            )

        backend.supplier_import_start_date = fields.Date.today()

    def netvisor_import_supplier(self, netvisor_key, company=False):
        """
        Import a partner from Netvisor
        :param netvisor_key: Netvisor external ID
        :return:
        """
        backend = self.get_netvisor_backend(company)

        with backend.work_on(self._name) as work:
            importer = work.component(usage="import.mapper")
            return importer.import_supplier(backend, netvisor_key)
