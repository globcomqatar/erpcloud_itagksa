# Copyright (c) 2026, ITAG KSA and Contributors
# License: MIT
"""Surface quality records raised from a voucher in that voucher's Connections.

A Calibration Schedule created from a stock receipt stores the voucher in its
source_document (Dynamic Link). Registering that fieldname on the voucher's
dashboard makes the Connections tab count and link back to the schedule.

A Quality Inspection points at its voucher through the reference_type /
reference_name pair instead, so it needs a dynamic_links entry as well: without
it the Connections tab would count every inspection whose reference_name happens
to match, regardless of the doctype it belongs to.
"""

from frappe import _


def _register_calibration_schedule(data):
	data["non_standard_fieldnames"]["Calibration Schedule"] = "source_document"
	return "Calibration Schedule"


def _register_quality_inspection(data, reference_type):
	data["non_standard_fieldnames"]["Quality Inspection"] = "reference_name"
	data.setdefault("dynamic_links", {})["reference_name"] = [reference_type, "reference_type"]
	return "Quality Inspection"


def stock_entry(data):
	items = [
		_register_calibration_schedule(data),
		_register_quality_inspection(data, "Stock Entry"),
	]
	data["transactions"].append({"label": _("Quality"), "items": items})
	return data


def purchase_receipt(data):
	items = [_register_calibration_schedule(data)]
	data["transactions"].append({"label": _("Quality"), "items": items})
	return data
