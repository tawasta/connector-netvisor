##############################################################################
#
#    Author: Oy Tawasta OS Technologies Ltd.
#    Copyright 2024 Oy Tawasta OS Technologies Ltd. (https://tawasta.fi)
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
    "name": "Netvisor Connector Expense support",
    "summary": "Add support for travel expenses",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "website": "https://gitlab.com/tawasta/odoo/connector-netvisor",
    "author": "Tawasta",
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
        "hr_expense",
    ],
    "data": [
        "data/template_trip_expense.xml",
        "security/model_access.xml",
        "views/hr_expense.xml",
        "views/hr_expense_sheet.xml",
        "views/netvisor_backend.xml",
    ],
    "assets": {},
    "demo": [],
}
