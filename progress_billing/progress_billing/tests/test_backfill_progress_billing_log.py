import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

from progress_billing.api import create_progress_invoice
from progress_billing.patches.v1_1.backfill_progress_billing_log import execute


class TestBackfillProgressBillingLog(FrappeTestCase):
	test_dependencies = ["Customer", "Item", "Warehouse"]

	def make_progress_so_with_invoice_but_no_log_row(self):
		so = make_sales_order(
			item_list=[{"item_code": "_Test Item", "qty": 1, "rate": 100000}],
			do_not_submit=True,
		)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.submit()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 100))
		invoice.currency = so.currency
		invoice.insert()
		invoice.submit()

		# Simulate "data from before this upgrade": the invoice exists and is
		# submitted (so.sync_progress_billing_log_row already logged it via
		# Task 3's real-time hook), but we clear the log to reproduce the
		# pre-upgrade state the patch needs to backfill.
		so.reload()
		so.pb_progress_billing_log = []
		so.save(ignore_permissions=True)

		return so, invoice

	def test_backfill_creates_log_row_for_existing_invoice(self):
		so, invoice = self.make_progress_so_with_invoice_but_no_log_row()

		execute()

		so.reload()
		self.assertEqual(len(so.pb_progress_billing_log), 1)
		row = so.pb_progress_billing_log[0]
		self.assertEqual(row.sales_invoice, invoice.name)
		self.assertEqual(row.progress_no, 1)
		self.assertEqual(row.invoice_status, "Submitted")

	def test_backfill_is_idempotent(self):
		so, invoice = self.make_progress_so_with_invoice_but_no_log_row()

		execute()
		execute()

		so.reload()
		self.assertEqual(len(so.pb_progress_billing_log), 1)

	def test_backfill_does_not_raise_when_so_has_cancelled_progress_invoice(self):
		# Regression test: a Sales Order whose Progress Billing Log still
		# references a cancelled progress invoice used to make the patch's
		# so.save() raise CancelledLinkError, because Frappe's "cannot link a
		# cancelled document" check rejected saving a Sales Order that links
		# to a cancelled Sales Invoice, and the patch never suppressed it
		# (unlike sync_progress_billing_log_row, which sets
		# so.flags.ignore_links = True for exactly this reason).
		so = make_sales_order(
			item_list=[{"item_code": "_Test Item", "qty": 1, "rate": 100000}],
			do_not_submit=True,
		)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.submit()

		# Invoice 1: submitted, then cancelled. Per sync_progress_billing_log_row's
		# design, cancelling an invoice does NOT remove its log row -- the row is
		# an intentional, permanent audit trail -- it only flips invoice_status to
		# "Cancelled". So this row must still exist (and still link to the now
		# cancelled invoice) after cancellation.
		invoice1 = frappe.get_doc(create_progress_invoice(so.name, 40))
		invoice1.currency = so.currency
		invoice1.insert()
		invoice1.submit()
		invoice1.cancel()

		# Invoice 2: submitted, real-time hook already logged it (Task 3
		# behavior). Simulate the pre-upgrade gap by clearing only this
		# invoice's row, leaving invoice 1's cancelled-invoice row intact --
		# that intact row is what the backfill patch's so.save() must
		# tolerate.
		invoice2 = frappe.get_doc(create_progress_invoice(so.name, 40))
		invoice2.currency = so.currency
		invoice2.insert()
		invoice2.submit()

		so.reload()
		self.assertEqual(len(so.pb_progress_billing_log), 2)
		cancelled_row = next(
			row for row in so.pb_progress_billing_log if row.sales_invoice == invoice1.name
		)
		self.assertEqual(cancelled_row.invoice_status, "Cancelled")

		so.pb_progress_billing_log = [
			row for row in so.pb_progress_billing_log if row.sales_invoice != invoice2.name
		]
		# This intermediate save is only test setup (simulating the pre-upgrade
		# gap), but it still needs to tolerate invoice 1's cancelled-invoice
		# link for the same reason the patch does.
		so.flags.ignore_links = True
		so.save(ignore_permissions=True)

		so.reload()
		self.assertEqual(len(so.pb_progress_billing_log), 1)

		# This must not raise CancelledLinkError.
		execute()

		so.reload()
		self.assertEqual(len(so.pb_progress_billing_log), 2)

		rows_by_invoice = {row.sales_invoice: row for row in so.pb_progress_billing_log}
		self.assertEqual(rows_by_invoice[invoice1.name].invoice_status, "Cancelled")
		self.assertEqual(rows_by_invoice[invoice2.name].invoice_status, "Submitted")
		self.assertEqual(rows_by_invoice[invoice2.name].progress_no, 2)
