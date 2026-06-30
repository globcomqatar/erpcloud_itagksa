import json

import frappe


def before_install():
	"""Run before this app's fixtures are synced during a fresh install.

	`install_app` syncs fixtures but never runs patches, so the stale-doc-name
	reconciliation must happen here for a clean first install.
	"""
	reconcile_stale_custom_field_names()


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
