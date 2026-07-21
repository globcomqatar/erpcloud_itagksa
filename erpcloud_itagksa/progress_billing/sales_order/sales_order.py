import frappe
from frappe import _
from frappe.utils import cint, flt


def update_progress_billing_totals(so):
	"""Set the stored summary fields from the Progress Billing Log (in-memory).

	Order level: Total = contract value, Billed = sum of non-cancelled log
	rows, Remaining = Total - Billed. Row level: each row stores the running
	billed total up to and including itself and the contract remaining at
	that point — recomputed on every change, so a cancellation ripples
	through all later rows. Callers persist via their own save.
	"""
	total = flt(so.grand_total)
	running = 0.0
	for row in sorted(
		so.get("pb_progress_billing_log") or [], key=lambda r: cint(r.progress_no)
	):
		if row.invoice_status != "Cancelled":
			running += flt(row.billing_amount)
		row.total_billed_amount = running
		row.remaining_amount = total - running

	so.pb_total_amount = total
	so.pb_billed_amount = running
	so.pb_remaining_amount = total - running


def refresh_progress_billing_log_payments(doc, method):
	for row in doc.get("pb_progress_billing_log") or []:
		if not row.sales_invoice:
			continue

		invoice = frappe.db.get_value(
			"Sales Invoice",
			row.sales_invoice,
			["grand_total", "rounded_total", "outstanding_amount"],
			as_dict=True,
		)
		if not invoice:
			continue

		# ERPNext computes outstanding_amount against the ROUNDED total, so
		# paid math must use the same basis (see sync_progress_billing_log_row).
		invoice_total = flt(invoice.rounded_total) or flt(invoice.grand_total)
		row.amount_paid = invoice_total - flt(invoice.outstanding_amount)
		row.outstanding_amount = flt(invoice.outstanding_amount)
		row.payment_percentage = (
			(row.amount_paid / invoice_total * 100) if invoice_total else 0
		)

	if doc.pb_billing_method == "Progress Billing":
		# Keep the stored summary fields current on every form load too, so
		# they display correctly even before any new invoice event persists them.
		update_progress_billing_totals(doc)


def validate_billing_method_lock(doc, method):
	if doc.is_new():
		return

	# frappe.db.get_value (not doc.get_doc_before_save()) so this works
	# identically whether Frappe fires us via "validate" (draft save) or
	# "before_update_after_submit" (editing a submitted order) — the latter
	# is required because pb_billing_method has allow_on_submit=1.
	previous_billing_method = frappe.db.get_value("Sales Order", doc.name, "pb_billing_method")
	if previous_billing_method == doc.pb_billing_method:
		return

	has_progress_invoice = frappe.db.exists(
		"Sales Invoice",
		{"pb_against_sales_order": doc.name, "docstatus": 1},
	)
	if has_progress_invoice:
		frappe.throw(
			_(
				"Billing Method cannot be changed because Progress Invoices already exist against this Sales Order."
			)
		)
