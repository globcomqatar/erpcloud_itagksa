import frappe
from frappe.utils import flt

from erpcloud_itagksa.progress_billing.setup import ensure_progress_billing_custom_fields


def execute():
	# This patch filters by pb_billing_method and writes pb_total_amount /
	# pb_billed_amount / pb_remaining_amount -- all fixture-shipped custom
	# fields, which sync AFTER post_model_sync patches -- so on the first
	# migrate that ships this patch, the columns don't exist yet. Ensure them
	# here first (idempotent).
	ensure_progress_billing_custom_fields()

	for name in frappe.get_all(
		"Sales Order", filters={"pb_billing_method": "Progress Billing"}, pluck="name"
	):
		so = frappe.get_doc("Sales Order", name)
		total = flt(so.grand_total)
		billed = sum(
			flt(row.billing_amount)
			for row in (so.get("pb_progress_billing_log") or [])
			if row.invoice_status != "Cancelled"
		)
		# Direct column write: these are derived, read-only fields — a full
		# doc.save() would re-run link validation (and could trip on log rows
		# referencing cancelled invoices) for no benefit here.
		frappe.db.set_value(
			"Sales Order",
			name,
			{
				"pb_total_amount": total,
				"pb_billed_amount": billed,
				"pb_remaining_amount": total - billed,
			},
			update_modified=False,
		)
