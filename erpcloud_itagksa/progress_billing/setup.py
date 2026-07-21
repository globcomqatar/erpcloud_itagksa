import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_summary_custom_fields():
	"""Guarantee the Sales Order summary Currency fields exist before a patch writes to them.

	Frappe's migrate order is pre_model_sync patches -> doctype/module sync ->
	post_model_sync patches -> fixture sync (sync_fixtures) -> after_migrate.
	Fixtures (including these 3 Custom Fields, which normally ship via
	fixtures/custom_field.json) are therefore NOT yet on the site the first
	time a post_model_sync patch runs on a fresh install/migrate. Any patch
	that needs to write pb_total_amount / pb_billed_amount / pb_remaining_amount
	must call this first. Idempotent (create_custom_fields with update=True);
	harmless if fixture sync has already created them.
	"""
	create_custom_fields(
		{
			"Sales Order": [
				{
					"fieldname": "pb_total_amount",
					"label": "Total Amount",
					"fieldtype": "Currency",
					"options": "currency",
					"insert_after": "pb_progress_billing_status",
					"read_only": 1,
					"allow_on_submit": 1,
					"no_copy": 1,
					"depends_on": "eval:doc.pb_billing_method=='Progress Billing'",
				},
				{
					"fieldname": "pb_billed_amount",
					"label": "Billed Amount",
					"fieldtype": "Currency",
					"options": "currency",
					"insert_after": "pb_total_amount",
					"read_only": 1,
					"allow_on_submit": 1,
					"no_copy": 1,
					"depends_on": "eval:doc.pb_billing_method=='Progress Billing'",
				},
				{
					"fieldname": "pb_remaining_amount",
					"label": "Remaining Amount",
					"fieldtype": "Currency",
					"options": "currency",
					"insert_after": "pb_billed_amount",
					"read_only": 1,
					"allow_on_submit": 1,
					"no_copy": 1,
					"depends_on": "eval:doc.pb_billing_method=='Progress Billing'",
				},
			],
		},
		update=True,
	)
