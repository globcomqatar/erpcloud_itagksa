# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

import frappe
from frappe.model.workflow import get_workflow_safe_globals
from frappe.tests.utils import FrappeTestCase

from erpcloud_itagksa.itag_ksa_selling.quotation.bid_approval import record_review
from erpcloud_itagksa.itag_ksa_selling.quotation.quotation import calculate_cost_and_profitability

WORKFLOW_NAME = "Quotation Bid Approval"
DEPARTMENT_REVIEW = "Pending Department Review"
CEO_APPROVAL = "Pending CEO Approval"
READY_FOR_SUBMIT = "Ready for Submit"

APPROVED_EXCEPT_FINANCE = {
	"custom_review_status_design": "Approved",
	"custom_review_status_quality": "Approved",
	"custom_review_status_operations": "Approved",
}

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


class TestQuotationBidApprovalWorkflow(FrappeTestCase):
	def landing_states(self, role, action="Approve", state=DEPARTMENT_REVIEW, **values):
		"""Where a press of that action by that role takes a quote holding these values."""
		quotation = frappe.new_doc("Quotation")
		quotation.update(values)

		return [
			transition.next_state
			for transition in frappe.get_doc("Workflow", WORKFLOW_NAME).transitions
			if transition.state == state
			and transition.allowed == role
			and transition.action == action
			and self.condition_holds(transition, quotation)
		]

	def condition_holds(self, transition, quotation):
		if not transition.condition:
			return True

		return frappe.safe_eval(
			transition.condition, get_workflow_safe_globals(), dict(doc=quotation.as_dict())
		)

	def test_only_the_sales_user_starts_the_review(self):
		starters = {
			transition.allowed
			for transition in frappe.get_doc("Workflow", WORKFLOW_NAME).transitions
			if transition.action == "Send for Review"
		}

		self.assertEqual(starters, {"Sales User"})

	def test_a_department_stays_in_review_while_another_is_still_out(self):
		self.assertEqual(
			self.landing_states("Manufacturing Review", base_rounded_total=25000), [DEPARTMENT_REVIEW]
		)

	def test_a_department_that_approved_has_nothing_left_to_press(self):
		self.assertEqual(
			self.landing_states("Manufacturing Review", custom_review_status_design="Approved"), []
		)

	def test_the_last_approval_reaches_the_ceo_above_the_threshold(self):
		self.assertEqual(
			self.landing_states("Finance Review", base_rounded_total=25000, **APPROVED_EXCEPT_FINANCE),
			[CEO_APPROVAL],
		)

	def test_the_last_approval_is_ready_to_submit_below_the_threshold(self):
		self.assertEqual(
			self.landing_states("Finance Review", base_rounded_total=15000, **APPROVED_EXCEPT_FINANCE),
			[READY_FOR_SUBMIT],
		)

	def test_the_threshold_reads_the_grand_total_when_rounding_is_off(self):
		self.assertEqual(
			self.landing_states("Finance Review", base_grand_total=25000, **APPROVED_EXCEPT_FINANCE),
			[CEO_APPROVAL],
		)

	def test_a_subcontract_quote_skips_the_exempt_departments(self):
		self.assertEqual(
			self.landing_states("Manufacturing Review", custom_subcontracted_job=1, base_rounded_total=25000),
			[],
		)
		self.assertEqual(
			self.landing_states(
				"Finance Review",
				custom_subcontracted_job=1,
				custom_review_status_operations="Approved",
				base_rounded_total=25000,
			),
			[CEO_APPROVAL],
		)

	def test_every_department_rejects_back_to_draft(self):
		for role in ("Manufacturing Review", "Quality Review", "Operation Review", "Finance Review"):
			self.assertEqual(self.landing_states(role, action="Reject"), ["Draft"], role)

	def test_the_ceo_decision_does_not_submit(self):
		self.assertEqual(self.landing_states("CEO Approval", state=CEO_APPROVAL), [READY_FOR_SUBMIT])

	def test_the_sales_user_submits_from_ready_for_submit(self):
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
		submit = [t for t in workflow.transitions if t.action == "Submit"]

		self.assertEqual(len(submit), 1)
		self.assertEqual(submit[0].state, READY_FOR_SUBMIT)
		self.assertEqual(submit[0].allowed, "Sales User")
		self.assertEqual({s.doc_status for s in workflow.states if s.state == submit[0].next_state}, {"1"})


class TestQuotationReviewRecord(FrappeTestCase):
	def press(self, quotation, action, state=DEPARTMENT_REVIEW):
		quotation.flags.bid_review_state = state
		quotation.flags.bid_review_action = action
		record_review(quotation)

	def test_the_action_records_the_department_of_whoever_pressed_it(self):
		quotation = frappe.new_doc("Quotation")

		self.press(quotation, "Approve")

		# the tests run as Administrator, who holds every review role
		self.assertEqual(quotation.custom_review_status_design, "Approved")
		self.assertEqual(quotation.custom_reviewed_by_design, frappe.session.user)

	def test_a_reviewer_of_several_departments_signs_one_at_a_time(self):
		quotation = frappe.new_doc("Quotation")

		self.press(quotation, "Approve")
		self.press(quotation, "Approve")

		self.assertEqual(quotation.custom_review_status_quality, "Approved")

	def test_a_rejection_is_recorded_as_rejected(self):
		quotation = frappe.new_doc("Quotation")

		self.press(quotation, "Reject")

		self.assertEqual(quotation.custom_review_status_design, "Rejected")

	def test_the_ceo_decision_only_touches_the_ceo_status(self):
		quotation = frappe.new_doc("Quotation")

		self.press(quotation, "No Bid", state=CEO_APPROVAL)

		self.assertEqual(quotation.custom_review_status_ceo, "No Bid")
		self.assertEqual(quotation.custom_review_status_design, "Pending Review")

	def test_a_subcontract_quote_records_the_departments_that_review_it(self):
		quotation = frappe.new_doc("Quotation")
		quotation.custom_subcontracted_job = 1

		self.press(quotation, "Approve")

		self.assertEqual(quotation.custom_review_status_operations, "Approved")
		self.assertEqual(quotation.custom_review_status_design, "Pending Review")

	def test_a_save_without_a_workflow_action_records_nothing(self):
		quotation = frappe.new_doc("Quotation")

		record_review(quotation)

		self.assertEqual(quotation.custom_review_status_design, "Pending Review")
