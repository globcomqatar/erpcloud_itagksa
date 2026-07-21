import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_progress_billing_custom_fields():
	"""Guarantee all Progress Billing custom fields exist before a patch reads/writes them.

	Frappe's migrate order is pre_model_sync patches -> doctype/module sync ->
	post_model_sync patches -> fixture sync (sync_fixtures) -> after_migrate.
	These fields normally ship via fixtures/custom_field.json, which is synced
	in that LAST step -- so on a genuinely fresh site (e.g. a first deploy on
	Frappe Cloud), none of them exist yet the first time a post_model_sync
	patch runs. Any patch that queries or writes any pb_* field on Sales Order
	or Sales Invoice must call this first. Idempotent (create_custom_fields
	with update=True); harmless once fixture sync has already created them --
	that later sync remains authoritative for exact field properties/position.
	"""
	create_custom_fields(
		{
			"Sales Order": [
				{
					"fieldname": "pb_section_break_progress_billing",
					"label": "Progress Billing Configuration",
					"fieldtype": "Section Break",
					"insert_after": "advance_paid",
					"collapsible": 1,
				},
				{
					"fieldname": "pb_billing_method",
					"label": "Billing Method",
					"fieldtype": "Select",
					"options": "Quantity Based\nProgress Billing",
					"default": "Quantity Based",
					"insert_after": "pb_section_break_progress_billing",
					"in_standard_filter": 1,
					"allow_on_submit": 1,
				},
				{
					"fieldname": "pb_column_break_progress_billing",
					"fieldtype": "Column Break",
					"insert_after": "pb_billing_method",
				},
				{
					"fieldname": "pb_progress_billing_status",
					"label": "Progress Billing Status",
					"fieldtype": "Select",
					"options": "\nIn Progress\nCompleted",
					"read_only": 1,
					"insert_after": "pb_column_break_progress_billing",
					"depends_on": "eval:doc.pb_billing_method=='Progress Billing'",
				},
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
				{
					"fieldname": "pb_progress_billing_log_html",
					"label": "Billing Summary",
					"fieldtype": "HTML",
					"insert_after": "pb_remaining_amount",
					"depends_on": "eval:doc.pb_billing_method=='Progress Billing'",
				},
				{
					"fieldname": "pb_progress_billing_log",
					"label": "Progress Billing Log",
					"fieldtype": "Table",
					"options": "Progress Billing Log",
					"insert_after": "pb_progress_billing_log_html",
					"allow_on_submit": 1,
					"depends_on": "eval:doc.pb_billing_method=='Progress Billing'",
				},
			],
			"Sales Invoice": [
				{
					"fieldname": "pb_is_progress_invoice",
					"label": "Is Progress Invoice",
					"fieldtype": "Check",
					"insert_after": "update_billed_amount_in_sales_order",
					"read_only": 1,
					"hidden": 1,
				},
				{
					"fieldname": "pb_progress_billing_percentage",
					"label": "Progress Billing Percentage",
					"fieldtype": "Percent",
					"insert_after": "pb_is_progress_invoice",
					"read_only": 1,
					"depends_on": "eval:doc.pb_is_progress_invoice",
				},
				{
					"fieldname": "pb_against_sales_order",
					"label": "Progress Billing Against",
					"fieldtype": "Link",
					"options": "Sales Order",
					"insert_after": "pb_progress_billing_percentage",
					"read_only": 1,
					"depends_on": "eval:doc.pb_is_progress_invoice",
				},
			],
		},
		update=True,
	)
