# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

"""Build the Quotation Bid Approval workflow.

The route a quote takes is configuration: the states, the roles that may edit in each
state and the conditions that decide where every action lands all live on the Workflow
record.

Department review is parallel. All four departments work inside Pending Department
Review with the same two actions, Approve and Reject. Which department a press belongs
to comes from the role of the user who pressed it - see
itag_ksa_selling/quotation/bid_approval.py - because a transition writes only one field
and every department shares the state.

The last department to approve does not have to send the quote on. Approve carries three
rows per department: stay in review while another department is still out, go to Pending
CEO Approval when nothing else is pending and the quote is over the CEO threshold, go to
Ready for Submit when it is under. Conditions read the stored quote, so "nothing else is
pending" means every other required department has already approved.

Reject carries the same gate as Approve: a department that has approved sees neither
action again, and one that rejected still sees both when the quote comes back.

Which departments are required comes from custom_subcontracted_job: a service work order
needs Operations and Finance only, matching the sections the form hides.

A CEO decision is not a submission. It lands in Ready for Submit and the Sales User
submits from there.

The workflow is written in full every time this patch runs, so a site carrying the first
version - one action per department and a manual Send to CEO - ends up with the same
configuration as a fresh site.
"""

import frappe

WORKFLOW_NAME = "Quotation Bid Approval"
DOCUMENT_TYPE = "Quotation"

DRAFT = "Draft"
DEPARTMENT_REVIEW = "Pending Department Review"
CEO_APPROVAL = "Pending CEO Approval"
READY_FOR_SUBMIT = "Ready for Submit"
APPROVED = "Approved"
NO_BID = "No Bid"

# Over this much, in company currency, the CEO decides. The quote total is read the way
# the invoice reads it: the rounded total, or the grand total where rounding is off.
CEO_APPROVAL_THRESHOLD = 20000
QUOTE_TOTAL = "(doc.base_rounded_total or doc.base_grand_total)"

SALES_ROLES = ["Sales User", "Sales Manager"]

# (department, review role, skipped on an inward subcontract quote)
DEPARTMENTS = [
	("design", "Manufacturing Review", True),
	("quality", "Quality Review", True),
	("operations", "Operation Review", False),
	("finance", "Finance Review", False),
]

# (state, docstatus, style, roles allowed to edit in this state)
STATES = [
	(DRAFT, "0", "", SALES_ROLES),
	(DEPARTMENT_REVIEW, "0", "Warning", [role for _department, role, _exempt in DEPARTMENTS]),
	(CEO_APPROVAL, "0", "Warning", ["CEO Approval"]),
	(READY_FOR_SUBMIT, "0", "Primary", SALES_ROLES),
	(APPROVED, "1", "Success", ["Sales Manager"]),
	(NO_BID, "0", "Danger", ["Sales Manager"]),
]

# (state, action, next_state, role, condition)
SALES_TRANSITIONS = [
	(DRAFT, "Send for Review", DEPARTMENT_REVIEW, "Sales User", None),
	(READY_FOR_SUBMIT, "Submit", APPROVED, "Sales User", None),
]

CEO_TRANSITIONS = [
	(CEO_APPROVAL, "Approve", READY_FOR_SUBMIT, "CEO Approval", None),
	(CEO_APPROVAL, "Approve with Conditions", READY_FOR_SUBMIT, "CEO Approval", None),
	(CEO_APPROVAL, "Revise & Resubmit", DRAFT, "CEO Approval", None),
	(CEO_APPROVAL, "No Bid", NO_BID, "CEO Approval", None),
]


def execute():
	create_missing_states()
	create_missing_actions()
	save_workflow()
	frappe.db.commit()


def all_transitions():
	return SALES_TRANSITIONS + department_transitions() + CEO_TRANSITIONS


def department_transitions():
	transitions = []

	for department, role, exempt in DEPARTMENTS:
		reviews_this_quote = ["not doc.custom_subcontracted_job"] if exempt else []
		awaiting_this_department = reviews_this_quote + [
			f'doc.custom_review_status_{department} != "Approved"'
		]
		rest_approved = f"({other_departments_approved(department)})"

		transitions += [
			(
				DEPARTMENT_REVIEW,
				"Approve",
				DEPARTMENT_REVIEW,
				role,
				every(awaiting_this_department + [f"not {rest_approved}"]),
			),
			(
				DEPARTMENT_REVIEW,
				"Approve",
				CEO_APPROVAL,
				role,
				every(awaiting_this_department + [rest_approved, f"{QUOTE_TOTAL} > {CEO_APPROVAL_THRESHOLD}"]),
			),
			(
				DEPARTMENT_REVIEW,
				"Approve",
				READY_FOR_SUBMIT,
				role,
				every(awaiting_this_department + [rest_approved, f"{QUOTE_TOTAL} <= {CEO_APPROVAL_THRESHOLD}"]),
			),
			(DEPARTMENT_REVIEW, "Reject", DRAFT, role, every(awaiting_this_department)),
		]

	return transitions


def other_departments_approved(current_department):
	always = [
		approved(department)
		for department, _role, exempt in DEPARTMENTS
		if not exempt and department != current_department
	]
	when_not_subcontracted = [
		approved(department)
		for department, _role, exempt in DEPARTMENTS
		if exempt and department != current_department
	]

	if when_not_subcontracted:
		always.append(f"(doc.custom_subcontracted_job or ({every(when_not_subcontracted)}))")

	return every(always)


def approved(department):
	return f'doc.custom_review_status_{department} == "Approved"'


def every(conditions):
	return " and ".join(conditions)


def create_missing_states():
	for state, _docstatus, style, _roles in STATES:
		if frappe.db.exists("Workflow State", state):
			continue

		frappe.get_doc(
			{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
		).insert(ignore_permissions=True)


def create_missing_actions():
	for _state, action, _next_state, _role, _condition in all_transitions():
		if frappe.db.exists("Workflow Action Master", action):
			continue

		frappe.get_doc(
			{"doctype": "Workflow Action Master", "workflow_action_name": action}
		).insert(ignore_permissions=True)


def save_workflow():
	workflow = get_workflow()
	workflow.document_type = DOCUMENT_TYPE
	workflow.workflow_state_field = "workflow_state"
	workflow.is_active = 1
	workflow.send_email_alert = 0
	workflow.override_status = 0
	workflow.states = []
	workflow.transitions = []

	for state, docstatus, _style, roles in STATES:
		for role in roles:
			workflow.append("states", {"state": state, "doc_status": docstatus, "allow_edit": role})

	for state, action, next_state, role, condition in all_transitions():
		workflow.append(
			"transitions",
			{
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": role,
				"condition": condition,
				"allow_self_approval": 1,
			},
		)

	workflow.save(ignore_permissions=True)


def get_workflow():
	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		return frappe.get_doc("Workflow", WORKFLOW_NAME)

	workflow = frappe.new_doc("Workflow")
	workflow.workflow_name = WORKFLOW_NAME

	return workflow
