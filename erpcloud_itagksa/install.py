import json

import frappe

CASH_SUPPLIER = "Cash Supplier"


def before_install():
	"""Run before this app's fixtures are synced during a fresh install.

	`install_app` syncs fixtures but never runs patches, so the stale-doc-name
	reconciliation must happen here for a clean first install.
	"""
	reconcile_stale_custom_field_names()


def after_install():
	"""Run after this app's fixtures are synced during a fresh install."""
	ensure_cash_supplier()


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
