# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class BidApproval(Document):
	def validate(self):
		self.calculate_cost_and_profitability()

	def calculate_cost_and_profitability(self):
		self.total_project_cost = sum(flt(row.amount) for row in self.project_cost)

		selling_price = flt(self.recommended_selling_price)
		self.expected_profit = selling_price - flt(self.total_project_cost)
		self.profit_margin = (
			(flt(self.expected_profit) / selling_price * 100) if selling_price else 0
		)
