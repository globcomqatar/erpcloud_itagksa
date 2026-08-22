# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpcloud_itagksa.itag_ksa_selling.quotation.quotation import calculate_cost_and_profitability

DEPARTMENT_KEYS = ("design", "quality", "operations", "finance", "ceo")
SUBCONTRACT_EXEMPT_KEYS = ("design", "quality")


class TestQuotationBidApproval(FrappeTestCase):
	def test_bid_approval_tab_carries_every_review_section(self):
		meta = frappe.get_meta("Quotation")

		for key in DEPARTMENT_KEYS:
			for fieldname in (
				f"custom_{key}_review_section",
				f"custom_reviewed_by_{key}",
				f"custom_designation_{key}",
				f"custom_review_status_{key}",
				f"custom_sign_{key}_attach",
				f"custom_manual_sign_{key}",
			):
				self.assertTrue(meta.has_field(fieldname), fieldname)

		self.assertEqual(meta.get_field("custom_project_cost").options, "Bid Cost Line")

	def test_bid_approval_tab_is_anchored_to_a_core_field(self):
		anchor = frappe.db.get_value("Custom Field", "Quotation-custom_bid_approval_tab", "insert_after")

		self.assertEqual(anchor, "connections_tab")

	def test_subcontracted_job_hides_only_the_exempt_review_sections(self):
		meta = frappe.get_meta("Quotation")
		condition = "eval:!doc.custom_subcontracted_job"

		for key in DEPARTMENT_KEYS:
			section = meta.get_field(f"custom_{key}_review_section")
			expected = condition if key in SUBCONTRACT_EXEMPT_KEYS else None

			self.assertEqual(section.depends_on, expected, key)

	def test_selling_price_follows_the_rounded_total(self):
		quotation = frappe.new_doc("Quotation")
		quotation.grand_total = 1249.60
		quotation.rounded_total = 1250
		quotation.custom_recommended_selling_price = 9999

		calculate_cost_and_profitability(quotation)

		self.assertEqual(quotation.custom_recommended_selling_price, 1250)

	def test_selling_price_falls_back_to_the_grand_total_when_rounding_is_off(self):
		quotation = frappe.new_doc("Quotation")
		quotation.grand_total = 1249.60
		quotation.rounded_total = 0

		calculate_cost_and_profitability(quotation)

		self.assertEqual(quotation.custom_recommended_selling_price, 1249.60)

	def test_cost_and_profitability_totals_the_cost_lines(self):
		quotation = frappe.new_doc("Quotation")
		quotation.append("custom_project_cost", {"amount": 400})
		quotation.append("custom_project_cost", {"amount": 600})
		quotation.rounded_total = 1250

		calculate_cost_and_profitability(quotation)

		self.assertEqual(quotation.custom_total_project_cost, 1000)
		self.assertEqual(quotation.custom_expected_profit, 250)
		self.assertEqual(quotation.custom_profit_margin, 20)

	def test_profit_margin_is_zero_without_a_total(self):
		quotation = frappe.new_doc("Quotation")
		quotation.append("custom_project_cost", {"amount": 500})

		calculate_cost_and_profitability(quotation)

		self.assertEqual(quotation.custom_expected_profit, -500)
		self.assertEqual(quotation.custom_profit_margin, 0)

	def test_selling_price_is_read_only(self):
		field = frappe.get_meta("Quotation").get_field("custom_recommended_selling_price")

		self.assertEqual(field.read_only, 1)
