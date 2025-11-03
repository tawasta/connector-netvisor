##############################################################################
#
#    Author: Futural Oy
#    Copyright 2022 Futural Oy (https://futural.fi)
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
    "name": "Netvisor Connector eCommerce support",
    "summary": "Use Netvisor integration with eCommerce",
    "version": "17.0.1.0.2",
    "category": "Sales",
    "website": "https://gitlab.com/tawasta/odoo/connector-netvisor",
    "author": "Futural",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "auto_install": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "connector_netvisor",
        "website_sale",
        "website_sale_company_email",
        "website_sale_invoice_transmit_method",
    ],
    "data": [
        "views/website_sale_checkout.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "connector_netvisor_ecommerce/static/src/js/checkout.esm.js",
        ],
    },
    "demo": [],
}
