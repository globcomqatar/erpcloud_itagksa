# Copyright (c) 2026, ITAG KSA and Contributors
# License: MIT

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, today

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee


class CalibrationSchedule(Document):
	def validate(self):
		if self.docstatus == 0:
			self.fill_item_tag()
		self.validate_calibration_window()

	def fill_item_tag(self):
		"""Copy the serial's Item Tag onto the header (read-only display field).

		On a manually created schedule the serial is already tagged. A schedule
		auto-raised from a receipt runs before the tag is bound to the serial, so
		this leaves item_tag blank; the receipt handler stamps it in afterwards.
		"""
		if self.serial_no:
			self.item_tag = frappe.db.get_value("Serial No", self.serial_no, "custom_item_tag")

	def validate_calibration_window(self):
		if (
			self.purchase_date
			and self.end_of_life_date
			and getdate(self.purchase_date) >= getdate(self.end_of_life_date)
		):
			throw(_("End of Life Date must be after Purchase Date"))

	def on_submit(self):
		if not self.get("schedules"):
			throw(_("Please click on 'Generate Calibration Schedule' to get the calibration visits"))
		self.db_set("status", "Submitted")
		self.db_set("calibration_progress", f"0 / {len(self.schedules)} completed")

	def on_update(self):
		if self.docstatus == 0:
			self.db_set("status", "Draft")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	@frappe.whitelist()
	def generate_schedule(self):
		"""Fill the visit rows from the header and save.

		The only writer of visit rows — saving the form never regenerates them. The
		save is done here because a whitelisted doc method only returns the mutated
		doc to the client; without it the generated rows are never written.
		"""
		if self.docstatus != 0:
			return
		self.validate_generation_inputs()

		employee_name = (
			frappe.db.get_value("Employee", self.employee, "employee_name") if self.employee else None
		)
		self.set("schedules", [])
		for scheduled_date in self.create_schedule_list():
			self.append(
				"schedules",
				{
					"item_code": self.item_code,
					"item_name": self.item_name,
					"serial_no": self.serial_no,
					"item_tag": self.item_tag,
					"scheduled_date": scheduled_date,
					"employee": self.employee,
					"employee_name": employee_name,
					"completion_status": "Pending",
				},
			)
		self.save()

	def validate_generation_inputs(self):
		if not self.purchase_date or not self.end_of_life_date:
			throw(_("Set Purchase Date and End of Life Date before generating the schedule"))
		if cint(self.no_of_calibrations) < 1:
			throw(_("Set how many calibrations are due between those two dates"))
		self.validate_calibration_window()

	def create_schedule_list(self):
		"""Space the calibrations evenly between purchase and end of life.

		The last one lands on the end-of-life date. A date falling on a holiday is
		pulled back to the working day before it.
		"""
		purchase_date = getdate(self.purchase_date)
		end_of_life_date = getdate(self.end_of_life_date)
		count = cint(self.no_of_calibrations)
		days_between_calibrations = (end_of_life_date - purchase_date).days / count
		holidays = self.get_holidays()

		schedule_list = []
		for calibration in range(1, count + 1):
			scheduled_date = add_days(purchase_date, round(days_between_calibrations * calibration))
			schedule_list.append(avoid_holidays(getdate(scheduled_date), holidays))

		return schedule_list

	def get_holidays(self):
		holiday_list = (
			get_holiday_list_for_employee(self.employee)
			if self.employee
			else frappe.get_cached_value("Company", self.company, "default_holiday_list")
		)
		if not holiday_list:
			return []
		return frappe.db.get_all("Holiday", {"parent": holiday_list}, pluck="holiday_date")


def avoid_holidays(scheduled_date, holidays):
	for _attempt in range(len(holidays)):
		if scheduled_date not in holidays:
			break
		scheduled_date = add_days(scheduled_date, -1)
	return scheduled_date


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
