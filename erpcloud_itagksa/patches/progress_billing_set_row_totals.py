import frappe

from erpcloud_itagksa.progress_billing.setup import ensure_progress_billing_custom_fields
from erpcloud_itagksa.progress_billing.sales_order.sales_order import update_progress_billing_totals


def execute():
	# This patch filters by pb_billing_method, reads/appends the Sales Order's
	# pb_progress_billing_log table field, and update_progress_billing_totals
	# writes pb_total_amount/pb_billed_amount/pb_remaining_amount -- all
	# fixture-shipped Custom Fields on Sales Order, which sync AFTER
	# post_model_sync patches, so on the first migrate that ships this patch
	# they don't exist yet. (Only the "Progress Billing Log" child doctype's
	# OWN fields -- total_billed_amount, remaining_amount -- are safe without
	# this guard, since those are real doctype JSON fields synced during
	# model-sync; the parent-side Table field that attaches that child table
	# to Sales Order is the fixture that needs guarding.)
	ensure_progress_billing_custom_fields()

	for name in frappe.get_all(
		"Sales Order", filters={"pb_billing_method": "Progress Billing"}, pluck="name"
	):
		so = frappe.get_doc("Sales Order", name)
		if not so.get("pb_progress_billing_log"):
			continue

		update_progress_billing_totals(so)

		# Direct column writes: these are derived, read-only fields — a full
		# doc.save() would re-run link validation (and could trip on log rows
		# referencing cancelled invoices) for no benefit here.
		for row in so.pb_progress_billing_log:
			frappe.db.set_value(
				"Progress Billing Log",
				row.name,
				{
					"total_billed_amount": row.total_billed_amount,
					"remaining_amount": row.remaining_amount,
				},
				update_modified=False,
			)
