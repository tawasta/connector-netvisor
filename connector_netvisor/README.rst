.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================
Netvisor connector
==================

Integration between Odoo and Netvisor

Configuration
=============
! Currently you have to install ``netvisor-api-client`` with

``pip3 install https://github.com/Tawasta/netvisor-api-client/archive/backports.zip``

After installing the module, create a Netvisor Backend-record for each company.

If you want to use dimensions, go to Settings and enable "Netvisor dimensions".

Features
========
- Importing/exporting products
- Importing/exporting customers
- Exporting (sending) sale invoices to Netvisor
- Exporting (sending) sale credit notes to Netvisor
- Using accounting suggestions in sale invoices
- Fetching payment status for sale invoices
- Importing dimensions
- Using dimensions in sale invoices

Bug Tracker
===========

Bugs are tracked on `GitLab Issues <https://gitlab.com/tawasta/odoo/connector-netvisor/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Contributors
------------

* Jarmo Kortetjärvi <jarmo.kortetjarvi@tawasta.fi>

Maintainer
----------

.. image:: https://tawasta.fi/templates/tawastrap/images/logo.png
   :alt: Oy Tawasta OS Technologies Ltd.
   :target: https://tawasta.fi/

This module is maintained by Oy Tawasta OS Technologies Ltd.
