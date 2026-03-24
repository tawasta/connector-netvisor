##############################################################################
#
#    Author: Futural Oy
#    Copyright 2026 Futural Oy (https://futural.fi)
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
    "name": "Netvisor Connector SSN from partner",
    "summary": "Use partner's SSN as employee's SSN in Netvisor Connector",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "website": "https://github.com/tawasta/connector-netvisor/",
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
        "connector_netvisor_expense",
        "social_security_number_management",
    ],
    "data": [
    ],
    "assets": {},
    "demo": [],
}
