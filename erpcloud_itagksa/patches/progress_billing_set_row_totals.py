import frappe

from erpcloud_itagksa.progress_billing.setup import ensure_summary_custom_fields
from erpcloud_itagksa.progress_billing.sales_order.sales_order import update_progress_billing_totals


def execute():
	# Populate the per-row total_billed_amount / remaining_amount fields on
	# existing Progress Billing Log rows (that doctype is synced during the
	# model-sync phase, before post_model_sync patches, so those columns are
	# already guaranteed to exist). update_progress_billing_totals also sets
	# the Sales Order's own pb_total_amount/pb_billed_amount/pb_remaining_amount,
	# which -- unlike the log row fields -- ship as fixtures and need the
	# same early guard as progress_billing_set_totals.
	ensure_summary_custom_fields()

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
