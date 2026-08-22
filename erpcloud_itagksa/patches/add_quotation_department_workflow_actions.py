# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

"""Give every department its own action inside Pending Department Review.

The four actions stay in that one state - each transition names Pending Department
Review as both state and next_state - so departments still work at the same time and
in any order. The last one to finish presses Send to CEO.

A transition cannot record which department pressed it: apply_workflow writes only the
update_field of the state the document lands in (frappe/model/workflow.py), and all four
land in the same state. So custom_review_status_{department} stays the record, and each
action carries it as a condition - the button appears once that department has set
Approved, and pressing it logs the sign-off on the timeline.

Design and Quality also require the quote not to be an inward subcontract, so a service
work order shows two buttons rather than four. Send to CEO already carries the same rule.

Appended only when missing, so a later migrate leaves an edited workflow alone.
"""

import frappe

WORKFLOW_NAME = "Quotation Bid Approval"
DEPARTMENT_REVIEW_STATE = "Pending Department Review"

# (action, role, review status field, needed on an inward subcontract quote)
DEPARTMENT_ACTIONS = [
	("Design Approve", "Manufacturing Review", "custom_review_status_design", False),
	("Quality Approve", "Quality Review", "custom_review_status_quality", False),
	("Operations Approve", "Operation Review", "custom_review_status_operations", True),
	("Finance Approve", "Finance Review", "custom_review_status_finance", True),
]


def execute():
	if not frappe.db.exists("Workflow", WORKFLOW_NAME):
		return

	workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
	existing_actions = {t.action for t in workflow.transitions}
	added = False

	for action, role, status_field, needed_when_subcontracted in DEPARTMENT_ACTIONS:
		if action in existing_actions:
			continue

		create_action_master(action)
		workflow.append(
			"transitions",
			{
				"state": DEPARTMENT_REVIEW_STATE,
				"action": action,
				"next_state": DEPARTMENT_REVIEW_STATE,
				"allowed": role,
				"condition": build_condition(status_field, needed_when_subcontracted),
				"allow_self_approval": 1,
			},
		)
		added = True

	if not added:
		return

	workflow.save(ignore_permissions=True)
	frappe.db.commit()


def build_condition(status_field, needed_when_subcontracted):
	condition = f'doc.{status_field} == "Approved"'
	if not needed_when_subcontracted:
		condition += " and not doc.custom_subcontracted_job"

	return condition


def create_action_master(action):
	if frappe.db.exists("Workflow Action Master", action):
		return

	frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
		ignore_permissions=True
	)
