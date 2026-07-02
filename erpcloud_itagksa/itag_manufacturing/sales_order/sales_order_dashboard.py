# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

from frappe import _


def get_dashboard_data(data):
	"""Add a Stock Entry connection to the Sales Order dashboard.

	Stock Entry links back to Sales Order through the custom Link field
	custom_customer_sales_order_number (set to the Sales Order name by the
	CPI Material Receipt mapper). erpnext's base dashboard has no Stock Entry
	group, so add one and register the non-standard fieldname so the
	Connections tab counts and filters correctly.
	"""
	data["non_standard_fieldnames"]["Stock Entry"] = "custom_customer_sales_order_number"
	data["transactions"].append({"label": _("Stock"), "items": ["Stock Entry"]})
	return data
