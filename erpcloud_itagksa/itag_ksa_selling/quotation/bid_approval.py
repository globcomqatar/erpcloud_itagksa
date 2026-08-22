# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

"""Record which department is behind a workflow action on a Quotation.

Every department reviews inside one state, so the Approve and Revise buttons cannot
carry the department with them: a transition writes at most one field, the update_field
of the state the document lands in (frappe/model/workflow.py). The department is taken
from the review role of whoever pressed the button, and that department's review status,
reviewer, designation and signature are stamped here.

apply_workflow is overridden in hooks.py for one reason: to carry the pressed action and
the state it was pressed in onto the document, where validate can read them. Frappe still
chooses the transition from the stored document, so the conditions on the workflow see the
quote as it was before the press - which is what lets the last department's Approve land
in Pending CEO Approval or Ready for Submit.

Sending a quote back to Draft - a department's Revise, or the CEO's Revise & Resubmit -
voids the sign-offs it already carries, so every department reviews the revised quote
again before it can move on.
"""

import frappe
from frappe.model.workflow import apply_workflow as apply_frappe_workflow
from frappe.utils import today

QUOTATION = "Quotation"
ACTION_FLAG = "bid_review_action"
STATE_FLAG = "bid_review_state"

DEPARTMENT_REVIEW = "Pending Department Review"
CEO_APPROVAL = "Pending CEO Approval"
PENDING_REVIEW = "Pending Review"

REVIEW_ROLES = {
	"design": "Manufacturing Review",
	"quality": "Quality Review",
	"operations": "Operation Review",
	"finance": "Finance Review",
	"ceo": "CEO Approval",
}

# Only the departments reviewing in that state can be signing. Ordered, so a user who
# holds more than one review role signs for one department per press and their next press
# still finds a transition to take.
DEPARTMENTS_BY_STATE = {
	DEPARTMENT_REVIEW: ["design", "quality", "operations", "finance"],
	CEO_APPROVAL: ["ceo"],
}

# An inward subcontract quote is a service work order: those two departments do not
# review it, and the workflow hides their actions the same way.
SUBCONTRACT_EXEMPT_DEPARTMENTS = ("design", "quality")

ACTION_STATUS = {
	"Approve": "Approved",
	"Revise": "Revise",
	"Approve with Conditions": "Approved with Conditions",
	"Revise & Resubmit": "Revise & Resubmit",
	"No Bid": "No Bid",
}

# These send the quote back to Draft, so the reviews it carries no longer stand.
SEND_BACK_ACTIONS = ("Revise", "Revise & Resubmit")

SIGN_OFF_FIELDS = (
	"custom_reviewed_by_{}",
	"custom_date_{}",
	"custom_designation_{}",
	"custom_sign_{}_attach",
)


@frappe.whitelist()
def apply_workflow(doc, action):
	doc = frappe.get_doc(frappe.parse_json(doc))
	doc.load_from_db()

	if doc.doctype == QUOTATION:
		doc.flags[ACTION_FLAG] = action
		doc.flags[STATE_FLAG] = doc.workflow_state

	return apply_frappe_workflow(doc, action)


def record_review(doc, method=None):
	action = doc.flags.get(ACTION_FLAG)
	status = ACTION_STATUS.get(action)
	department = signing_department(doc, status)

	if not department:
		return

	doc.set(f"custom_review_status_{department}", status)
	sign_off(doc, department)

	if action in SEND_BACK_ACTIONS:
		clear_department_reviews(doc, signed_by=department)


def signing_department(doc, status):
	if not status:
		return None

	roles = frappe.get_roles()
	for department in reviewing_departments(doc):
		if REVIEW_ROLES[department] not in roles:
			continue

		if doc.get(f"custom_review_status_{department}") != status:
			return department

	return None


def reviewing_departments(doc):
	departments = DEPARTMENTS_BY_STATE.get(doc.flags.get(STATE_FLAG), [])
	if not doc.custom_subcontracted_job:
		return departments

	return [
		department for department in departments if department not in SUBCONTRACT_EXEMPT_DEPARTMENTS
	]


def clear_department_reviews(doc, signed_by):
	# The department that sent the quote back keeps its own line: it says who did it.
	for department in DEPARTMENTS_BY_STATE[DEPARTMENT_REVIEW]:
		if department == signed_by:
			continue

		doc.set(f"custom_review_status_{department}", PENDING_REVIEW)
		for field in SIGN_OFF_FIELDS:
			doc.set(field.format(department), None)


def sign_off(doc, department):
	reviewer = doc.get(f"custom_reviewed_by_{department}") or frappe.session.user
	doc.set(f"custom_reviewed_by_{department}", reviewer)
	doc.set(f"custom_date_{department}", today())

	employee = frappe.db.get_value(
		"Employee", {"user_id": reviewer}, ["designation", "custom_attach_sign_image"], as_dict=True
	)
	if not employee:
		return

	doc.set(f"custom_designation_{department}", employee.designation)
	doc.set(f"custom_sign_{department}_attach", employee.custom_attach_sign_image)
