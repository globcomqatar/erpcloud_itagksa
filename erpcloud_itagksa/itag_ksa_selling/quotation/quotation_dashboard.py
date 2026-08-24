# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

from frappe import _


def get_dashboard_data(data):
	data["transactions"].append({"label": _("Bid Approval"), "items": ["Bid Approval"]})
	return data
