# Copyright (c) 2026, ITAG KSA and Contributors
# License: MIT
"""Surface the auto-raised Calibration Schedule in its source voucher's Connections.

A Calibration Schedule created from a stock receipt stores the voucher in its
source_document (Dynamic Link). Registering that fieldname on the voucher's
dashboard makes the Connections tab count and link back to the schedule.
"""

from frappe import _


def _add_calibration_link(data):
	data["non_standard_fieldnames"]["Calibration Schedule"] = "source_document"
	data["transactions"].append({"label": _("Quality"), "items": ["Calibration Schedule"]})
	return data


def stock_entry(data):
	return _add_calibration_link(data)


def purchase_receipt(data):
	return _add_calibration_link(data)
