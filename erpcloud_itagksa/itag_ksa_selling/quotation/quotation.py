# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

from frappe.utils import flt


def validate(doc, method=None):
	copy_customer_name(doc)
	calculate_cost_and_profitability(doc)


def copy_customer_name(doc):
	# erpnext fills customer_name for a customer, a lead or a prospect, and hides it on
	# the first tab. The bid workup shows its own copy on the Project Information section.
	doc.custom_customer_name2 = doc.customer_name


def calculate_cost_and_profitability(doc):
	doc.custom_total_project_cost = sum(flt(row.amount) for row in doc.custom_project_cost)
	doc.custom_recommended_selling_price = quoted_total(doc)

	selling_price = flt(doc.custom_recommended_selling_price)
	doc.custom_expected_profit = selling_price - flt(doc.custom_total_project_cost)
	doc.custom_profit_margin = (
		(flt(doc.custom_expected_profit) / selling_price * 100) if selling_price else 0
	)


def quoted_total(doc):
	# What the customer is actually billed, the way erpnext reads it on the invoice
	# (sales_invoice.py): rounded_total, which set_rounded_total zeroes when rounding
	# is turned off on the quote or in Global Defaults.
	return flt(doc.rounded_total) or flt(doc.grand_total)
