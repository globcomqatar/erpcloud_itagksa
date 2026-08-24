# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from erpnext.selling.doctype.quotation.test_quotation import make_quotation

from erpcloud_itagksa.itag_ksa_selling.quotation.quotation import create_bid_approval

# This site's standard ERPNext test fixtures (_Test Company, _Test Customer, etc.) can't
# be created here: an unrelated ksa_compliance mandatory field on Mode of Payment and a
# broken Connected App both blow up mid-fixture-creation. Use real site records instead.
COMPANY = "Factory ITAG Gulf International Co."
CUSTOMER = "Saudi Aramco"
ITEM = "10301370"
WAREHOUSE = "All Customer Stores - ITAG"
CURRENCY = "SAR"


class TestBidApproval(FrappeTestCase):
	def test_calculate_cost_and_profitability(self):
		bid_approval = frappe.new_doc("Bid Approval")
		bid_approval.quotation = "not-a-real-quotation"
		bid_approval.customer = CUSTOMER
		bid_approval.recommended_selling_price = 1000
		bid_approval.append("project_cost", {"amount": 400})
		bid_approval.append("project_cost", {"amount": 100})
		bid_approval.validate()

		self.assertEqual(bid_approval.total_project_cost, 500)
		self.assertEqual(bid_approval.expected_profit, 500)
		self.assertEqual(bid_approval.profit_margin, 50)

	def test_calculate_cost_and_profitability_zero_selling_price(self):
		bid_approval = frappe.new_doc("Bid Approval")
		bid_approval.quotation = "not-a-real-quotation"
		bid_approval.customer = CUSTOMER
		bid_approval.recommended_selling_price = 0
		bid_approval.append("project_cost", {"amount": 100})
		bid_approval.validate()

		self.assertEqual(bid_approval.profit_margin, 0)

	def make_test_quotation(self, **args):
		args.setdefault("company", COMPANY)
		args.setdefault("party_name", CUSTOMER)
		args.setdefault("currency", CURRENCY)
		args.setdefault("item", ITEM)
		args.setdefault("warehouse", WAREHOUSE)
		return make_quotation(**args)

	def test_create_bid_approval_carries_customer_and_subcontracted_job(self):
		quotation = self.make_test_quotation(do_not_save=True)
		quotation.custom_subcontracted_job = 1
		quotation.insert()

		bid_approval_name = create_bid_approval(quotation.name)
		bid_approval = frappe.get_doc("Bid Approval", bid_approval_name)

		self.assertEqual(bid_approval.quotation, quotation.name)
		self.assertEqual(bid_approval.customer, quotation.customer_name)
		self.assertEqual(bid_approval.subcontracted_job, 1)
		self.assertEqual(bid_approval.recommended_selling_price, quotation.net_total)

	def test_create_bid_approval_blocks_non_draft_quotation(self):
		quotation = self.make_test_quotation()
		quotation.submit()

		with self.assertRaises(frappe.ValidationError):
			create_bid_approval(quotation.name)
