# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

from frappe.utils import flt


def validate(doc, method=None):
	calculate_cost_and_profitability(doc)


def calculate_cost_and_profitability(doc):
	doc.custom_total_project_cost = sum(flt(row.amount) for row in doc.custom_project_cost)
	doc.custom_recommended_selling_price = flt(doc.grand_total)

	selling_price = flt(doc.custom_recommended_selling_price)
	doc.custom_expected_profit = selling_price - flt(doc.custom_total_project_cost)
	doc.custom_profit_margin = (
		(flt(doc.custom_expected_profit) / selling_price * 100) if selling_price else 0
	)
