# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, cint, today

CALIBRATION_VISIT_DUE = "calibration_visit_due"
DEFAULT_REMINDER_DAYS = 7


def notify_due_calibrations():
	"""Remind on calibration visits falling due after the configured lead time.

	A Notification cannot be pointed at a visit row: its Document Type link hides
	child tables (istable: 0) and its Days Before date field only lists the parent's
	own date fields, so scheduled_date is unreachable from the UI. This runs daily
	and fires the "Calibration Visit Due" Notification through the native Method
	event instead, which keeps the subject, message and recipients editable in the
	UI rather than frozen in this file.
	"""
	reminder_days = cint(
		frappe.db.get_single_value("ITAG KSA Settings", "calibration_reminder_days")
	)
	if reminder_days < 1:
		reminder_days = DEFAULT_REMINDER_DAYS

	for schedule_name, visits in due_visits_by_schedule(add_days(today(), reminder_days)).items():
		schedule = frappe.get_doc("Calibration Schedule", schedule_name)
		# Cancelled between the query and here, or still a draft the operator has
		# not submitted — either way there is nothing to remind anyone about.
		if schedule.docstatus != 1:
			continue
		# Read by the notification template to list the visits that triggered it.
		# The template's `doc` is the schedule, whose rows span the whole plan.
		schedule.due_visits = visits
		schedule.run_notifications(CALIBRATION_VISIT_DUE)
		frappe.db.commit()


def due_visits_by_schedule(due_date):
	"""Group the pending visits scheduled on `due_date` under their schedule."""
	rows = frappe.get_all(
		"Calibration Schedule Detail",
		filters={
			"parenttype": "Calibration Schedule",
			"completion_status": "Pending",
			"scheduled_date": due_date,
		},
		fields=["parent", "item_code", "item_name", "serial_no", "scheduled_date", "employee_name"],
		ignore_permissions=True,
	)

	grouped = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)
	return grouped
