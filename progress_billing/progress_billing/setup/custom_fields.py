import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

DEPRECATED_FIELDS = [
	"Sales Order-pb_progress_billing_summary",
]


def get_custom_fields():
	return {
		"Sales Order": [
			{
				"fieldname": "pb_section_break_progress_billing",
				"label": "Progress Billing Configuration",
				"fieldtype": "Section Break",
				"insert_after": "advance_paid",
				"collapsible": 1,
			},
			{
				# allow_on_submit: editing this field after submit is exactly
				# the scenario validate_billing_method_lock exists to guard —
				# without it, Frappe's own submit-lock blocks the edit
				# unconditionally, before our lock logic ever runs.
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
				# Stored mirrors of the Billing Summary figures so they are
				# available to reports, list views, and the API (the HTML
				# summary is client-side only). Recomputed by
				# update_progress_billing_totals whenever the log changes.
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
	}


def sync_custom_fields():
	create_custom_fields(get_custom_fields(), update=True)
	remove_deprecated_fields()


def remove_deprecated_fields():
	# create_custom_fields only creates/updates fields present in
	# get_custom_fields() — it never deletes fields removed from that dict.
	# Custom Field records are named "{DocType}-{fieldname}".
	# Note: this bench's frappe.delete_doc_if_exists() signature is
	# (doctype, name, force=0) — it does not forward ignore_permissions.
	# Use frappe.delete_doc directly (ignore_missing=True gives the
	# "if exists" behavior) so the deprecated field is actually removed.
	for field_name in DEPRECATED_FIELDS:
		frappe.delete_doc(
			"Custom Field", field_name, ignore_permissions=True, ignore_missing=True
		)
