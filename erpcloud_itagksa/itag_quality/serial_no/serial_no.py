# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, add_months, getdate, today

# Frequency label -> function(base_date, cycle_index) giving that cycle's due date.
FREQUENCY_STEP = {
	"Weekly": lambda base, i: add_days(base, 7 * i),
	"Monthly": lambda base, i: add_months(base, i),
	"Quarterly": lambda base, i: add_months(base, 3 * i),
	"Half-Yearly": lambda base, i: add_months(base, 6 * i),
	"Yearly": lambda base, i: add_months(base, 12 * i),
}

CALIBRATION_TABLE = "custom_calibration_schedule"


def after_insert(doc, method=None):
	"""Manually-created serials (Serial No form) fire this ORM hook."""
	generate_calibration_schedule(doc.name, doc.item_code)


def generate_calibration_schedule(serial_no, item_code):
	"""Fill a serial's Calibration Schedule child table, one row per cycle.

	Serials born from stock transactions are written with `frappe.db.bulk_insert`
	(no ORM hooks), so this is driven from the Serial and Batch Bundle on_submit
	for those, and from Serial No after_insert for manually-entered ones. Only acts
	on serials whose Item is flagged `custom_is_calibration_item` with a frequency
	and a positive cycle count. Due dates step forward from today by the Item's
	frequency, one row per cycle. Idempotent: skips if the schedule is already set.
	"""
	if not serial_no or not item_code:
		return

	item = frappe.db.get_value(
		"Item",
		item_code,
		[
			"custom_is_calibration_item",
			"custom_calibration_frequency",
			"custom_no_of_calibrations",
		],
		as_dict=True,
	)
	if not item or not item.custom_is_calibration_item:
		return

	step = FREQUENCY_STEP.get(item.custom_calibration_frequency)
	cycles = int(item.custom_no_of_calibrations or 0)
	if not step or cycles < 1:
		return

	serial = frappe.get_doc("Serial No", serial_no)
	if serial.get(CALIBRATION_TABLE):
		return

	base = getdate(today())
	for cycle in range(1, cycles + 1):
		serial.append(
			CALIBRATION_TABLE,
			{
				"sequence": cycle,
				"frequency": item.custom_calibration_frequency,
				"due_date": step(base, cycle),
				"status": "Pending",
			},
		)
	serial.save(ignore_permissions=True)
