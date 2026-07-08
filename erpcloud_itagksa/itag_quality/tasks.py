# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today


def create_calibration_tasks():
	"""Raise a Task for every calibration whose due date has arrived.

	Runs daily. Picks Pending Calibration Schedule rows (child rows on Serial No)
	due today or earlier with no Task yet, creates a Task (subject "Calibration for
	<item>", start date = the due date), links it back, and marks the row "Task
	Created". The unset-task filter plus the per-row link keep it idempotent across
	reruns.
	"""
	due = frappe.get_all(
		"Calibration Schedule",
		filters=[
			["parenttype", "=", "Serial No"],
			["status", "=", "Pending"],
			["calibration_task", "is", "not set"],
			["due_date", "<=", today()],
		],
		fields=["name", "parent", "sequence", "due_date"],
		ignore_permissions=True,
	)
	if not due:
		return

	for row in due:
		serial = frappe.db.get_value(
			"Serial No", row.parent, ["item_code", "custom_item_tag"], as_dict=True
		) or frappe._dict()
		item_name = (
			frappe.db.get_value("Item", serial.item_code, "item_name")
			if serial.item_code
			else None
		)

		task = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": "Calibration for {0}".format(
					item_name or serial.item_code or row.parent
				),
				"exp_start_date": row.due_date,
				"description": _task_description(row, serial, item_name),
			}
		)
		task.insert(ignore_permissions=True)

		frappe.db.set_value(
			"Calibration Schedule",
			row.name,
			{"calibration_task": task.name, "status": "Task Created"},
		)

	frappe.db.commit()


def _task_description(row, serial, item_name):
	return (
		"Calibration cycle {seq} for item {item} (Serial No {serial}"
		"{tag}) is due on {due}."
	).format(
		seq=row.sequence,
		item=item_name or serial.item_code or row.parent,
		serial=row.parent,
		tag=", Item Tag {0}".format(serial.custom_item_tag) if serial.custom_item_tag else "",
		due=row.due_date,
	)
