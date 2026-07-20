import frappe
from frappe.utils import cint, flt

from progress_billing.overrides.sales_order import update_progress_billing_totals


def execute():
	# Submitted invoices only: drafts must not be linked from the log (their
	# Link row would block deleting the draft), matching sync_progress_billing_log_row.
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"pb_is_progress_invoice": 1, "docstatus": 1},
		fields=[
			"name",
			"pb_against_sales_order",
			"pb_progress_billing_percentage",
			"posting_date",
			"grand_total",
			"rounded_total",
			"outstanding_amount",
			"docstatus",
		],
		order_by="posting_date asc, creation asc",
	)

	orders = {}

	for invoice in invoices:
		if not invoice.pb_against_sales_order:
			continue

		so_name = invoice.pb_against_sales_order
		if so_name not in orders:
			orders[so_name] = frappe.get_doc("Sales Order", so_name)
		so = orders[so_name]

		already_logged = any(
			row.sales_invoice == invoice.name for row in (so.get("pb_progress_billing_log") or [])
		)
		if already_logged:
			continue

		max_progress_no = max(
			[cint(row.progress_no) for row in (so.get("pb_progress_billing_log") or [])], default=0
		)
		# ERPNext computes outstanding_amount against the ROUNDED total, so
		# paid math must use the same basis (see sync_progress_billing_log_row).
		invoice_total = flt(invoice.rounded_total) or flt(invoice.grand_total)
		amount_paid = invoice_total - flt(invoice.outstanding_amount)
		payment_percentage = (amount_paid / invoice_total * 100) if invoice_total else 0

		so.append(
			"pb_progress_billing_log",
			{
				"progress_no": max_progress_no + 1,
				"billing_date": invoice.posting_date,
				"billing_percentage": invoice.pb_progress_billing_percentage,
				"billing_amount": invoice.grand_total,
				"sales_invoice": invoice.name,
				"invoice_status": "Submitted",
				"amount_paid": amount_paid,
				"outstanding_amount": invoice.outstanding_amount,
				"payment_percentage": payment_percentage,
			},
		)

	for so in orders.values():
		update_progress_billing_totals(so)
		# A Sales Order's Progress Billing Log can reference a since-cancelled progress
		# invoice (an intentional audit trail, not a live dependency). Bypass Frappe's
		# "cannot link to a cancelled document" check for this save, matching the same
		# pattern used in sync_progress_billing_log_row (overrides/sales_invoice.py).
		so.flags.ignore_links = True
		so.save(ignore_permissions=True)
