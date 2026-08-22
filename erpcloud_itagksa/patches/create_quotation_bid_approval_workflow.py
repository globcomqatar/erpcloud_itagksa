# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

"""Seed the Quotation Bid Approval workflow.

The workflow is configuration, not code: the states, the roles that may edit in
each state and the conditions that gate every transition all live on the Workflow
record. Nothing here runs at document time.

Department review is parallel, so it is not modelled as one state per department.
All four departments edit inside Pending Department Review - four rows for that
state, one role each - and record their own custom_review_status_{department}.
Order does not matter and no department waits for another. The Send to CEO
transition carries the condition that every required department has approved, so
the quote cannot reach the CEO early.

Which departments are required comes from custom_subcontracted_job, in that same
condition: a service work order needs Operations and Finance only, a normal quote
also needs Design and Engineering and Quality. Two fewer approvals, matching the
sections that custom_subcontracted_job already hides on the form.

Seeded create-if-missing. A later migrate will not overwrite an edited workflow,
so the admin can tune roles and conditions in the UI.

Creating the Workflow makes Frappe add the hidden workflow_state Custom Field on
Quotation and stamp existing rows by docstatus: drafts become Draft, submitted
quotes become Approved (they predate the workflow and were never reviewed),
cancelled quotes are left empty because no state carries docstatus 2.
"""

import frappe

WORKFLOW_NAME = "Quotation Bid Approval"
DOCUMENT_TYPE = "Quotation"

# (state, docstatus, style, roles allowed to edit in this state)
STATES = [
	("Draft", "0", "", ["Sales Manager", "Sales User"]),
	(
		"Pending Department Review",
		"0",
		"Warning",
		["Manufacturing Review", "Quality Review", "Operation Review", "Finance Review"],
	),
	("Pending CEO Approval", "0", "Warning", ["CEO Approval"]),
	("Approved", "1", "Success", ["Sales Manager"]),
	("No Bid", "0", "Danger", ["Sales Manager"]),
]

DEPARTMENTS_APPROVED = (
	'doc.custom_review_status_operations == "Approved"'
	' and doc.custom_review_status_finance == "Approved"'
	" and (doc.custom_subcontracted_job"
	' or (doc.custom_review_status_design == "Approved"'
	' and doc.custom_review_status_quality == "Approved"))'
)

CEO_DECIDED_TO_APPROVE = (
	'doc.custom_review_status_ceo in ("Approved", "Approved with Conditions")'
)
CEO_DECIDED_TO_RETURN = 'doc.custom_review_status_ceo == "Revise & Resubmit"'
CEO_DECIDED_NO_BID = 'doc.custom_review_status_ceo == "No Bid"'

# (state, action, next_state, role, condition)
TRANSITIONS = [
	("Draft", "Send for Review", "Pending Department Review", "Sales Manager", None),
	("Draft", "Send for Review", "Pending Department Review", "Sales User", None),
	(
		"Pending Department Review",
		"Send to CEO",
		"Pending CEO Approval",
		"Sales Manager",
		DEPARTMENTS_APPROVED,
	),
	(
		"Pending Department Review",
		"Send to CEO",
		"Pending CEO Approval",
		"Sales User",
		DEPARTMENTS_APPROVED,
	),
	("Pending CEO Approval", "Approve", "Approved", "CEO Approval", CEO_DECIDED_TO_APPROVE),
	("Pending CEO Approval", "Revise & Resubmit", "Draft", "CEO Approval", CEO_DECIDED_TO_RETURN),
	("Pending CEO Approval", "No Bid", "No Bid", "CEO Approval", CEO_DECIDED_NO_BID),
]


def execute():
	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		return

	create_missing_states()
	create_missing_actions()
	create_workflow()
	frappe.db.commit()


def create_missing_states():
	for state, _docstatus, style, _roles in STATES:
		if frappe.db.exists("Workflow State", state):
			continue

		frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
			ignore_permissions=True
		)


def create_missing_actions():
	for _state, action, _next_state, _role, _condition in TRANSITIONS:
		if frappe.db.exists("Workflow Action Master", action):
			continue

		frappe.get_doc(
			{"doctype": "Workflow Action Master", "workflow_action_name": action}
		).insert(ignore_permissions=True)


def create_workflow():
	workflow = frappe.new_doc("Workflow")
	workflow.workflow_name = WORKFLOW_NAME
	workflow.document_type = DOCUMENT_TYPE
	workflow.workflow_state_field = "workflow_state"
	workflow.is_active = 1
	workflow.send_email_alert = 0
	workflow.override_status = 0

	for state, docstatus, _style, roles in STATES:
		for role in roles:
			workflow.append("states", {"state": state, "doc_status": docstatus, "allow_edit": role})

	for state, action, next_state, role, condition in TRANSITIONS:
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

	workflow.insert(ignore_permissions=True)
