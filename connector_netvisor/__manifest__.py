##############################################################################
#
#    Author: Oy Tawasta OS Technologies Ltd.
#    Copyright 2021 Oy Tawasta OS Technologies Ltd. (https://tawasta.fi)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see http://www.gnu.org/licenses/agpl.html
#
##############################################################################

{
    "name": "Netvisor connector",
    "summary": "Integration between Odoo and Netvisor",
    "version": "14.0.1.0.0",
    "category": "Invoicing & Payments",
    "website": "https://gitlab.com/tawasta/odoo/connector-netvisor",
    "author": "Tawasta",
    "license": "AGPL-3",
    "application": True,
    "installable": True,
    "external_dependencies": {
        "python": [
            "cachetools",
            "netvisor-api-client",
        ],
        "bin": [],
    },
    "depends": [
        "account",
        "connector",
        "product",
        "queue_job",
        "sale",
        "l10n_fi_business_code",
        "l10n_fi_edicode",
    ],
    "post_init_hook": "init_netvisor_data",
    "data": [
        "data/ir_cron.xml",
        "security/model_access.xml",
        "views/account_move.xml",
        "views/account_tax.xml",
        "views/config_settings.xml",
        "views/netvisor_backend_menu.xml",
        "views/netvisor_backend_form.xml",
        "views/netvisor_backend_tree.xml",
        "views/partner.xml",
        "views/product.xml",
    ],
}
