# Copyright (c) 2026, ITAG KSA and Contributors
# License: MIT

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, today

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

DAYS_IN_PERIOD = {"Weekly": 7, "Monthly": 30, "Quarterly": 91, "Half Yearly": 182, "Yearly": 365}


class CalibrationSchedule(Document):
	def validate(self):
		if self.docstatus == 0:
			self.fill_item_tag()
			self.apply_periodicity_dates()
			self.sync_item_row()
		self.validate_details()
		self.validate_dates_with_periodicity()
		if self.docstatus == 0 and (not self.schedules or self.items_changed() or self.visit_count_mismatch()):
			self.generate_schedule()

	def fill_item_tag(self):
		"""Copy the serial's Item Tag onto the header (read-only display field).

		On a manually created schedule the serial is already tagged. A schedule
		auto-raised from a receipt runs before the tag is bound to the serial, so
		this leaves item_tag blank; the receipt handler stamps it in afterwards.
		"""
		if self.serial_no:
			self.item_tag = frappe.db.get_value("Serial No", self.serial_no, "custom_item_tag")

	def apply_periodicity_dates(self):
		"""Derive end_date (and default no_of_visits) from the header item fields."""
		if not (self.periodicity and self.start_date):
			return
		if not self.no_of_visits:
			self.no_of_visits = 1
		self.end_date = add_days(self.start_date, cint(self.no_of_visits) * DAYS_IN_PERIOD[self.periodicity])

	def sync_item_row(self):
		"""Rebuild the (single) items row from the header fields.

		The header is the source of truth; the items table feeds the existing
		schedule-generation loop. One serialised item per schedule.
		"""
		self.set("items", [])
		if not self.item_code:
			return
		if not self.item_name:
			self.item_name = frappe.db.get_value("Item", self.item_code, "item_name")
		self.append(
			"items",
			{
				"item_code": self.item_code,
				"item_name": self.item_name,
				"serial_no": self.serial_no,
				"item_tag": self.item_tag,
				"start_date": self.start_date,
				"end_date": self.end_date,
				"periodicity": self.periodicity,
				"no_of_visits": self.no_of_visits,
				"employee": self.employee,
			},
		)

	def on_submit(self):
		if not self.get("schedules"):
			throw(_("Please click on 'Generate Schedule' to get the calibration schedule"))
		self.db_set("status", "Submitted")
		self.db_set("calibration_progress", f"0 / {len(self.schedules)} completed")

	def on_update(self):
		if self.docstatus == 0:
			self.db_set("status", "Draft")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def validate_details(self):
		if not self.get("items"):
			throw(_("Please enter calibration details first"))

		for d in self.get("items"):
			if not d.item_code:
				throw(_("Please select item code"))
			if not d.start_date or not d.end_date:
				throw(_("Please select Start Date and End Date for Item {0}").format(d.item_code))
			if not d.no_of_visits:
				throw(_("Please mention the number of calibrations required for Item {0}").format(d.item_code))
			if getdate(d.start_date) >= getdate(d.end_date):
				throw(_("Start date should be less than end date for Item {0}").format(d.item_code))

	def validate_dates_with_periodicity(self):
		from frappe.utils import date_diff

		for d in self.get("items"):
			if d.start_date and d.end_date and d.periodicity:
				diff = date_diff(d.end_date, d.start_date) + 1
				if diff < DAYS_IN_PERIOD[d.periodicity]:
					throw(
						_(
							"Row {0}: To set {1} periodicity, the gap between start and end date must be at least {2} days"
						).format(d.idx, d.periodicity, DAYS_IN_PERIOD[d.periodicity])
					)

	@frappe.whitelist()
	def generate_schedule(self):
		if self.docstatus != 0:
			return
		self.set("schedules", [])
		count = 1
		for d in self.get("items"):
			dates = self.create_schedule_list(d.start_date, d.end_date, d.no_of_visits, d.employee)
			for i in range(d.no_of_visits):
				child = self.append("schedules")
				child.item_code = d.item_code
				child.item_name = d.item_name
				child.serial_no = d.serial_no
				child.item_tag = d.item_tag
				child.scheduled_date = dates[i].strftime("%Y-%m-%d")
				child.employee = d.employee
				child.employee_name = (
					frappe.db.get_value("Employee", d.employee, "employee_name") if d.employee else None
				)
				child.completion_status = "Pending"
				child.item_reference = d.name
				child.idx = count
				count += 1

	def create_schedule_list(self, start_date, end_date, no_of_visits, employee):
		schedule_list = []
		start_date_copy = start_date
		add_by = (getdate(end_date) - getdate(start_date)).days / no_of_visits

		for _visit in range(cint(no_of_visits)):
			if getdate(start_date_copy) < getdate(end_date):
				start_date_copy = add_days(start_date_copy, add_by)
				if len(schedule_list) < no_of_visits:
					schedule_date = self.avoid_holidays(getdate(start_date_copy), employee)
					if schedule_date > getdate(end_date):
						schedule_date = getdate(end_date)
					schedule_list.append(schedule_date)

		return schedule_list

	def avoid_holidays(self, schedule_date, employee):
		if employee:
			holiday_list = get_holiday_list_for_employee(employee)
		else:
			holiday_list = frappe.get_cached_value("Company", self.company, "default_holiday_list")

		if not holiday_list:
			return schedule_date

		holidays = frappe.db.get_all("Holiday", {"parent": holiday_list}, pluck="holiday_date")
		for _i in range(len(holidays)):
			if schedule_date in holidays:
				schedule_date = add_days(schedule_date, -1)
			else:
				break
		return schedule_date

	def items_changed(self):
		before = self.get_doc_before_save()
		if not before:
			return False
		if len(before.items) != len(self.items):
			return True
		fields = ["item_code", "serial_no", "start_date", "end_date", "periodicity", "no_of_visits", "employee"]
		for prev, cur in zip(before.items, self.items, strict=False):
			if any(str(prev.get(f)) != str(cur.get(f)) for f in fields):
				return True
		return False

	def visit_count_mismatch(self):
		return len(self.schedules) != sum(cint(d.no_of_visits) for d in self.items)


def recompute_progress(schedule_name):
	"""Refresh the header 'X / Y completed' tally from the visit rows.

	A display-only field updated after the fact, so `db.set_value` (no hooks) is
	the right tool. Skips a schedule already gone (e.g. cancelled and deleted).
	"""
	if not frappe.db.exists("Calibration Schedule", schedule_name):
		return
	rows = frappe.get_all(
		"Calibration Schedule Detail",
		filters={"parent": schedule_name, "parenttype": "Calibration Schedule"},
		pluck="completion_status",
	)
	total = len(rows)
	done = sum(1 for status in rows if status == "Fully Completed")
	frappe.db.set_value(
		"Calibration Schedule", schedule_name, "calibration_progress", f"{done} / {total} completed"
	)


@frappe.whitelist()
def make_material_request(source_name, visits=None):
	"""Build (but do not save) a calibration-service Material Request for chosen visits.

	`visits` is the list of Calibration Schedule Detail row names the operator picked
	in the Create dialog — one MR row per visit, carrying the calibration item + serial
	and a back-link to the visit (its row name) and schedule. The link rides the
	MR -> PO -> Stock Entry mappers by matching fieldname, so the return receipt can
	complete the exact visit. The main stock item, quantity and warehouse are left for
	the operator to fill on the opened draft.
	"""
	source = frappe.get_doc("Calibration Schedule", source_name)
	selected = set(frappe.parse_json(visits) or [])
	chosen = [v for v in source.schedules if not selected or v.name in selected]
	if not chosen:
		frappe.throw(_("Select at least one calibration visit to raise a Material Request."))

	mr = _new_calibration_mr(source.company)
	for visit in chosen:
		_append_calibration_visit(mr, visit, source.name)
	_set_header_calibration_date(mr, notify=True)

	return mr.as_dict()


@frappe.whitelist()
def make_bulk_material_requests(visits, combined=0):
	"""Raise draft calibration Material Requests for visits picked in the report.

	`visits` is a list of Calibration Schedule Detail row names spanning any number of
	schedules. `combined` off (default) raises one draft Material Request per schedule;
	on merges every visit into a single draft. Returns the created MR names so the
	report can link to them. Drafts only — the operator fills the main stock item.
	"""
	visit_names = frappe.parse_json(visits) or []
	if not visit_names:
		frappe.throw(_("Select at least one pending calibration visit."))

	rows = [frappe.get_doc("Calibration Schedule Detail", name) for name in visit_names]
	by_schedule = {}
	for row in rows:
		by_schedule.setdefault(row.parent, []).append(row)

	if cint(combined):
		companies = {frappe.db.get_value("Calibration Schedule", s, "company") for s in by_schedule}
		if len(companies) > 1:
			frappe.throw(_("Selected visits span multiple companies; uncheck Combine to raise one per schedule."))
		groups = [[(schedule, row) for schedule, rs in by_schedule.items() for row in rs]]
	else:
		groups = [[(schedule, row) for row in rs] for schedule, rs in by_schedule.items()]

	created = []
	for group in groups:
		company = frappe.db.get_value("Calibration Schedule", group[0][0], "company")
		mr = _new_calibration_mr(company)
		for schedule, visit in group:
			row = _append_calibration_visit(mr, visit, schedule)
			# A saved draft needs a valid item + qty; default to the calibration item
			# itself (qty 1, due on the visit date) for the operator to refine.
			row.item_code = visit.item_code
			row.qty = 1
			row.schedule_date = visit.scheduled_date or today()
		_set_header_calibration_date(mr, notify=False)
		# The report is offered to Quality staff, who don't hold Material Request create;
		# this controlled endpoint only builds calibration-service drafts for them.
		mr.insert(ignore_permissions=True)
		created.append(mr.name)

	frappe.db.commit()
	return created


def _new_calibration_mr(company):
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Purchase"
	mr.company = company
	mr.custom_is_collaboration_service_po = 1
	return mr


def _append_calibration_visit(mr, visit, schedule_name):
	return mr.append(
		"items",
		{
			"custom_sub_item": visit.item_code,
			"custom_sub_item_description": frappe.db.get_value("Item", visit.item_code, "description"),
			"custom_serial_no": visit.serial_no,
			"custom_calibration_visit": visit.name,
			"custom_calibration_schedule": schedule_name,
			"custom_calibration_date": visit.scheduled_date,
		},
	)


def _set_header_calibration_date(mr, notify):
	"""Set the header date when every chosen visit shares one, else leave it blank."""
	dates = {row.custom_calibration_date for row in mr.items}
	if len(dates) == 1:
		mr.custom_calibration_date = dates.pop()
	elif notify:
		frappe.msgprint(
			_("Selected visits span multiple calibration dates; header Calibration Date left blank. Each item row carries its own date."),
			indicator="orange",
			alert=True,
		)
