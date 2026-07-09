# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt


def before_validate(doc, method=None):
	"""Carry the chosen calibration serial into the native serial_no field.

	Users pick a single serial per row via the custom Link field custom_serial_no.
	Maintenance Schedule's generate_schedule copies the native serial_no (Small Text)
	onto each generated schedule row, so mirror the Link value into it before
	validation runs and the schedule is generated.
	"""
	for item in doc.get("items"):
		if item.custom_serial_no:
			item.serial_no = item.custom_serial_no
