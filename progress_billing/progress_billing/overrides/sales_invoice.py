import frappe
from frappe import _
from frappe.utils import cint, flt

from progress_billing.overrides.sales_order import update_progress_billing_totals


def update_progress_billing_status(doc, method):
	sales_orders = {item.sales_order for item in doc.items if item.sales_order}

	for so_name in sales_orders:
		billing_method = frappe.db.get_value("Sales Order", so_name, "pb_billing_method")
		if billing_method != "Progress Billing":
			continue

		per_billed = flt(frappe.db.get_value("Sales Order", so_name, "per_billed"))
		status = "Completed" if per_billed >= 99.99 else "In Progress"
		frappe.db.set_value("Sales Order", so_name, "pb_progress_billing_status", status)


def validate_is_progress_invoice(doc, method):
	if doc.is_return:
		return

	sales_orders = {item.sales_order for item in doc.items if item.sales_order}

	for so_name in sales_orders:
		billing_method = frappe.db.get_value("Sales Order", so_name, "pb_billing_method")
		if billing_method == "Progress Billing" and not doc.pb_is_progress_invoice:
			frappe.throw(
				_(
					"Sales Order {0} uses Progress Billing. Use 'Create Progress Invoice' "
					"on the Sales Order instead of a standard invoice."
				).format(so_name)
			)


def sync_progress_billing_log_row(doc, method):
	if not doc.pb_is_progress_invoice:
		return

	# Drafts must not appear in the log: the row's Link back to the invoice
	# would block deleting the draft (check_if_doc_is_linked), and draft
	# amounts would disagree with per_billed (submitted-only) in the Billing
	# Summary. The row is created when this hook fires again at submit.
	if doc.docstatus == 0:
		return

	so_name = doc.pb_against_sales_order
	if not so_name:
		return

	so = frappe.get_doc("Sales Order", so_name)

	status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
	status = status_map.get(doc.docstatus, "Draft")

	if status == "Cancelled":
		# When cancelling, Frappe's "linked document" check (run right after on_cancel)
		# would otherwise block cancellation because the Progress Billing Log child row
		# on the Sales Order still references this (about-to-be-cancelled) invoice.
		# That reference is an intentional, permanent audit trail, not a live dependency,
		# so tell Frappe to skip the Sales Order doctype in that check. Append rather than
		# overwrite so we don't clobber the core Sales Invoice controller's own exclusions
		# (e.g. GL Entry) for this same event.
		existing_ignores = list(doc.get("ignore_linked_doctypes") or [])
		if "Sales Order" not in existing_ignores:
			doc.ignore_linked_doctypes = existing_ignores + ["Sales Order"]

	# ERPNext computes outstanding_amount against the ROUNDED total
	# (taxes_and_totals.calculate_outstanding_amount: rounded_total or
	# grand_total), so paid math must use the same basis — otherwise an
	# unpaid invoice whose total rounds (e.g. 448.50 -> 448.00) shows a
	# phantom 0.50 "paid".
	invoice_total = flt(doc.rounded_total) or flt(doc.grand_total)
	amount_paid = invoice_total - flt(doc.outstanding_amount)
	payment_percentage = (amount_paid / invoice_total * 100) if invoice_total else 0

	row = None
	for existing in so.get("pb_progress_billing_log") or []:
		if existing.sales_invoice == doc.name:
			row = existing
			break

	if row is None:
		max_progress_no = max(
			[cint(r.progress_no) for r in (so.get("pb_progress_billing_log") or [])], default=0
		)
		row = so.append(
			"pb_progress_billing_log",
			{
				"progress_no": max_progress_no + 1,
				"billing_date": doc.posting_date,
				"billing_percentage": doc.pb_progress_billing_percentage,
				"billing_amount": doc.grand_total,
				"sales_invoice": doc.name,
			},
		)

	row.invoice_status = status
	row.amount_paid = amount_paid
	row.outstanding_amount = doc.outstanding_amount
	row.payment_percentage = payment_percentage

	update_progress_billing_totals(so)

	# The log row intentionally keeps its Sales Invoice link after that invoice is
	# cancelled (it's an audit trail, not a live reference), so bypass Frappe's
	# standard "cannot link to a cancelled document" check for this save. This is
	# the same pattern used throughout erpnext/frappe for log/history child tables
	# (see e.g. accounts_controller.py, stock_controller.py `flags.ignore_links`).
	so.flags.ignore_links = True
	so.save(ignore_permissions=True)
