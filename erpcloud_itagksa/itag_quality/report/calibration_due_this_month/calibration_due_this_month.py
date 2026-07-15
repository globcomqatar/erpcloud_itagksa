# Copyright (c) 2026, ITAG KSA and Contributors
# License: MIT
"""Pending calibration visits due within a month, one row per visit.

Drives the report's bulk Material Request action: each row carries its visit
(Calibration Schedule Detail) name so the operator can tick visits and raise
the calibration-service Material Requests straight from the report.
"""

import calendar
import datetime

import frappe
from frappe import _
from frappe.utils import cint, get_last_day, getdate, today

MONTH_NAMES = list(calendar.month_name)  # index 1..12 -> "January".."December"


def execute(filters=None):
	filters = filters or {}
	from_date, to_date = _month_bounds(filters)

	return _columns(), _visits(from_date, to_date, filters.get("company"))


def _month_bounds(filters):
	"""Turn the Month + Year filters into the first/last day of that month."""
	today_date = getdate(today())
	year = cint(filters.get("year")) or today_date.year
	month = filters.get("month")
	month_num = MONTH_NAMES.index(month) if month in MONTH_NAMES else today_date.month
	first = datetime.date(year, month_num, 1)
	return first, get_last_day(first)


def _columns():
	return [
		{"fieldname": "visit", "label": _("Visit"), "fieldtype": "Data", "hidden": 1},
		{"fieldname": "schedule", "label": _("Calibration Schedule"), "fieldtype": "Link", "options": "Calibration Schedule", "width": 160},
		{"fieldname": "item_name", "label": _("Item"), "fieldtype": "Data", "width": 180},
		{"fieldname": "serial_no", "label": _("Serial No"), "fieldtype": "Data", "width": 140},
		{"fieldname": "item_tag", "label": _("Item Tag"), "fieldtype": "Data", "width": 120},
		{"fieldname": "scheduled_date", "label": _("Scheduled Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 140},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 160},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 140},
	]


def _visits(from_date, to_date, company):
	rows = frappe.get_all(
		"Calibration Schedule Detail",
		filters={
			"parenttype": "Calibration Schedule",
			"completion_status": "Pending",
			"scheduled_date": ["between", [from_date, to_date]],
		},
		fields=[
			"name as visit",
			"parent as schedule",
			"item_name",
			"serial_no",
			"item_tag",
			"scheduled_date",
			"employee",
			"employee_name",
		],
		order_by="scheduled_date asc",
	)
	if not rows:
		return rows

	schedules = {r.schedule for r in rows}
	meta = {
		s.name: s
		for s in frappe.get_all(
			"Calibration Schedule",
			filters={"name": ["in", list(schedules)], "docstatus": 1},
			fields=["name", "company"],
		)
	}
	# Keep only visits on submitted schedules; drafts and cancelled ones aren't actionable.
	visits = []
	for row in rows:
		schedule = meta.get(row.schedule)
		if not schedule:
			continue
		if company and schedule.company != company:
			continue
		row.company = schedule.company
		visits.append(row)
	return visits
