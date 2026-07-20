import frappe

from progress_billing.overrides.sales_order import update_progress_billing_totals


def execute():
	# Populate the new per-row total_billed_amount / remaining_amount fields
	# on existing Progress Billing Log rows. The Progress Billing Log doctype
	# is synced during migrate's model-sync phase, which runs BEFORE
	# post_model_sync patches — so the columns are guaranteed to exist here
	# (unlike Sales Order custom fields, which need the v1_2-style guard).
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
