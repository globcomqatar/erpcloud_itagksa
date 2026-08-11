import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

CASH_SUPPLIER = "Cash Supplier"
INWARD_SERIAL_FIELD = {
	"fieldname": "custom_inward_serial_no",
	"label": "Inward Serial No",
	"fieldtype": "Select",
	"insert_after": "reference_name",
}


def before_install():
	"""Run before this app's fixtures are synced during a fresh install.

	`install_app` syncs fixtures but never runs patches, so the stale-doc-name
	reconciliation must happen here for a clean first install.
	"""
	reconcile_stale_custom_field_names()


def after_install():
	"""Run after this app's fixtures are synced during a fresh install."""
	ensure_cash_supplier()
	ensure_company_default_bank_account()
	ensure_profit_and_loss_chart_periodicity()


def after_migrate():
	ensure_inward_serial_field()
	ensure_company_default_bank_account()
	ensure_profit_and_loss_chart_periodicity()


def ensure_inward_serial_field():
	"""Seed the Quality Inspection serial field unless another app already ships it.

	The inward flow stores the received serial in a Select rather than the standard
	item_serial_no: inspection happens on the draft receipt, before the Serial No
	records exist, and a Link field can only reject a target that is not there yet.

	quality_itagksa ships this same field for its Job Card flow, so it is deliberately
	not one of our fixtures — a fixture upserts by name and would reassign the field to
	this app, leaving whichever app migrates last as the owner. create_custom_field
	inserts only when no Custom Field with this fieldname exists, so the live record
	and its owner are never touched.
	"""
	if create_custom_field("Quality Inspection", INWARD_SERIAL_FIELD):
		frappe.db.commit()


def ensure_cash_supplier():
	"""Seed the 'Cash Supplier' master used as the default on cash-purchase
	Material Requests. Create-if-missing only — an existing record (e.g. the live
	one carrying real CR details) is never touched. Skips quietly if no Supplier
	Group exists yet, so it can't break an install running ahead of ERPNext setup.
	"""
	if frappe.db.exists("Supplier", CASH_SUPPLIER):
		return

	supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	if not supplier_group:
		return

	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = CASH_SUPPLIER
	supplier.supplier_group = supplier_group
	supplier.supplier_type = "Company"
	# KSA compliance (ksa_compliance app) makes CR number/expiry mandatory on Supplier;
	# fill placeholders only when those fields exist so the seed works on any site.
	if supplier.meta.has_field("custom_supplier_cr_number"):
		supplier.custom_supplier_cr_number = "0000000000"
		supplier.custom_supplier_cr_expiry = "2099-12-31"
	supplier.insert(ignore_permissions=True)
	if supplier.name != CASH_SUPPLIER:
		frappe.rename_doc("Supplier", supplier.name, CASH_SUPPLIER, force=True)
	frappe.db.commit()


def ensure_company_default_bank_account():
	"""Fill Company.default_bank_account when it's blank and unambiguous.

	The standard ERPNext "Bank Balance" dashboard chart (surfaced on our CEO
	Dashboard fixture) resolves its account via
	Company.default_bank_account -> if that's empty the chart throws
	"Account is not set for the dashboard chart Bank Balance" and never
	renders. Set-if-missing only, and only when there is exactly one enabled
	Bank-type account for the company -- multiple candidates means picking
	one would silently misrepresent the company's real default, so we skip.
	"""
	for company in frappe.get_all("Company", {"default_bank_account": ["in", ["", None]]}, pluck="name"):
		bank_accounts = frappe.get_all(
			"Account",
			filters={
				"company": company,
				"account_type": "Bank",
				"is_group": 0,
				"disabled": 0,
			},
			pluck="name",
		)
		if len(bank_accounts) != 1:
			continue
		frappe.db.set_value("Company", company, "default_bank_account", bank_accounts[0])
	frappe.db.commit()


def ensure_profit_and_loss_chart_periodicity():
	"""Switch the standard "Profit and Loss" dashboard chart off "Yearly".

	That chart's own dynamic_filters_json always sets from_fiscal_year ==
	to_fiscal_year (both "current fiscal year"), and the Profit and Loss
	Statement report returns an empty chart.data (labels=[], datasets=[])
	whenever periodicity is "Yearly" with a single fiscal year selected --
	the report_summary totals still compute fine, so the numbers show but
	the bar never draws. "Quarterly" hits the report's normal multi-period
	path and always renders. Unconditional: unlike the bank account default,
	there's no ambiguous case here -- Yearly is broken 100% of the time
	given this chart's fixed filters, so any site with it still set to
	Yearly gets corrected once.
	"""
	filters_json = frappe.db.get_value("Dashboard Chart", "Profit and Loss", "filters_json")
	if not filters_json:
		return

	filters = json.loads(filters_json)
	if filters.get("periodicity") != "Yearly":
		return

	filters["periodicity"] = "Quarterly"
	frappe.db.set_value("Dashboard Chart", "Profit and Loss", "filters_json", json.dumps(filters))
	frappe.db.commit()


def reconcile_stale_custom_field_names():
	"""Rename live Custom Field docs whose name no longer matches this app's fixtures.

	The fixture importer matches an existing Custom Field by its doc `name`. If a
	field was ever fieldname-renamed on the target site, its doc name is frozen at
	the old value and won't match the fixture name -> the importer INSERTs ->
	duplicate fieldname -> migrate/install aborts. Renaming the live doc to the
	fixture name (column is keyed by fieldname, so 0 data impact) lets the importer
	UPDATE instead. Idempotent: skips any field already correctly named.
	"""
	for fx in _fixture_custom_fields():
		target_name = fx["name"]
		if frappe.db.exists("Custom Field", target_name):
			continue
		existing_name = frappe.db.get_value(
			"Custom Field", {"dt": fx["dt"], "fieldname": fx["fieldname"]}, "name"
		)
		if existing_name and existing_name != target_name:
			frappe.rename_doc("Custom Field", existing_name, target_name, force=True)
	frappe.db.commit()


def _fixture_custom_fields():
	path = frappe.get_app_path("erpcloud_itagksa", "fixtures", "custom_field.json")
	with open(path) as f:
		return json.load(f)
