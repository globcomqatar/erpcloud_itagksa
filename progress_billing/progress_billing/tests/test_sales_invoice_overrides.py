import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

from progress_billing.api import create_progress_invoice

# This test site does not have the standard ERPNext test fixtures (_Test Customer,
# _Test Item, _Test Warehouse - _TC, etc.) preloaded. Declaring test_dependencies
# forces frappe's test runner to create them (recursively, via each doctype's
# test_records.json) before this module's tests run. See erpnext's own
# test_sales_order.py for the same idiom (test_dependencies = ["Currency Exchange"]).
test_dependencies = ["Customer", "Item", "Warehouse"]


class TestProgressBillingStatusSync(FrappeTestCase):
	def make_progress_so(self):
		so = make_sales_order(
			item_list=[{"item_code": "_Test Item", "qty": 1, "rate": 100000}],
			do_not_submit=True,
		)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.submit()
		return so

	def test_status_flips_to_completed_at_100_percent(self):
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 100))
		invoice.insert()
		invoice.submit()

		so.reload()
		self.assertEqual(so.pb_progress_billing_status, "Completed")

	def test_status_stays_in_progress_below_100(self):
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 40))
		invoice.insert()
		invoice.submit()

		so.reload()
		self.assertEqual(so.pb_progress_billing_status, "In Progress")

	def test_status_reverts_to_in_progress_on_cancel(self):
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 100))
		invoice.insert()
		invoice.submit()

		invoice.cancel()

		so.reload()
		self.assertEqual(flt(so.per_billed), 0.0)
		self.assertEqual(so.pb_progress_billing_status, "In Progress")

	def test_standard_invoice_blocked_against_progress_billing_order(self):
		so = self.make_progress_so()

		invoice = frappe.new_doc("Sales Invoice")
		invoice.customer = so.customer
		invoice.company = so.company
		invoice.currency = so.currency
		invoice.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 100000,
				"sales_order": so.name,
			},
		)

		with self.assertRaises(frappe.ValidationError):
			invoice.insert()

	def test_progress_invoice_not_blocked(self):
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 10))
		invoice.insert()  # should not raise
		self.assertTrue(invoice.name)

	def test_standard_invoice_allowed_against_quantity_based_order(self):
		so = make_sales_order(
			item_list=[{"item_code": "_Test Item", "qty": 1, "rate": 100000}],
			do_not_submit=True,
		)
		so.submit()

		invoice = frappe.new_doc("Sales Invoice")
		invoice.customer = so.customer
		invoice.company = so.company
		invoice.currency = so.currency
		invoice.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 100000,
				"sales_order": so.name,
			},
		)
		invoice.insert()  # should not raise
		self.assertTrue(invoice.name)

	def test_no_log_row_for_draft_invoice_and_draft_is_deletable(self):
		# A draft progress invoice must not create a Progress Billing Log row:
		# the row's Link field back to the invoice would make Frappe's
		# check_if_doc_is_linked block deleting the draft (LinkExistsError),
		# and draft amounts would inflate the Billing Summary while per_billed
		# (submitted-only) stayed put. The row is created at submit instead.
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 10))
		invoice.insert()

		so.reload()
		self.assertEqual(len(so.pb_progress_billing_log), 0)

		# should not raise LinkExistsError
		frappe.delete_doc("Sales Invoice", invoice.name)
		self.assertFalse(frappe.db.exists("Sales Invoice", invoice.name))

	def test_log_row_created_on_submit(self):
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 10))
		invoice.insert()
		invoice.submit()

		so.reload()
		self.assertEqual(len(so.pb_progress_billing_log), 1)
		row = so.pb_progress_billing_log[0]
		self.assertEqual(row.progress_no, 1)
		self.assertEqual(row.sales_invoice, invoice.name)
		self.assertEqual(row.invoice_status, "Submitted")
		self.assertEqual(round(flt(row.billing_percentage), 2), 10.0)
		self.assertEqual(round(flt(row.billing_amount), 2), round(flt(invoice.grand_total), 2))

	def test_log_row_status_transitions_through_submit_and_cancel(self):
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 10))
		invoice.insert()
		invoice.submit()

		so.reload()
		row = so.pb_progress_billing_log[0]
		self.assertEqual(row.invoice_status, "Submitted")

		invoice.cancel()

		so.reload()
		row = so.pb_progress_billing_log[0]
		self.assertEqual(row.invoice_status, "Cancelled")

	def test_progress_billing_totals_stored_on_sales_order(self):
		# pb_total_amount / pb_billed_amount / pb_remaining_amount are stored
		# Currency fields mirroring the Billing Summary: Total = contract
		# value, Billed = sum of non-cancelled log rows, Remaining = Total -
		# Billed. They must update on invoice submit and on cancel.
		so = self.make_progress_so()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 40))
		invoice.insert()
		invoice.submit()

		so.reload()
		self.assertEqual(flt(so.pb_total_amount), 100000.0)
		self.assertEqual(flt(so.pb_billed_amount), 40000.0)
		self.assertEqual(flt(so.pb_remaining_amount), 60000.0)

		invoice.cancel()

		so.reload()
		self.assertEqual(flt(so.pb_total_amount), 100000.0)
		self.assertEqual(flt(so.pb_billed_amount), 0.0)
		self.assertEqual(flt(so.pb_remaining_amount), 100000.0)

	def test_cumulative_billed_and_remaining_per_row(self):
		# Each log row stores the cumulative billed amount up to and
		# including itself, and the contract remaining at that point.
		# Option A semantics: recomputed on every change, so a cancellation
		# ripples through all rows and the last non-cancelled row always
		# matches the Sales Order's own pb_billed/pb_remaining fields.
		so = self.make_progress_so()

		invoice_1 = frappe.get_doc(create_progress_invoice(so.name, 30))
		invoice_1.insert()
		invoice_1.submit()

		invoice_2 = frappe.get_doc(create_progress_invoice(so.name, 20))
		invoice_2.insert()
		invoice_2.submit()

		so.reload()
		rows = sorted(so.pb_progress_billing_log, key=lambda r: r.progress_no)
		self.assertEqual(flt(rows[0].total_billed_amount), 30000.0)
		self.assertEqual(flt(rows[0].remaining_amount), 70000.0)
		self.assertEqual(flt(rows[1].total_billed_amount), 50000.0)
		self.assertEqual(flt(rows[1].remaining_amount), 50000.0)

		invoice_1.cancel()

		so.reload()
		rows = sorted(so.pb_progress_billing_log, key=lambda r: r.progress_no)
		# cancelled row no longer contributes to the running total
		self.assertEqual(rows[0].invoice_status, "Cancelled")
		self.assertEqual(flt(rows[0].total_billed_amount), 0.0)
		self.assertEqual(flt(rows[0].remaining_amount), 100000.0)
		self.assertEqual(flt(rows[1].total_billed_amount), 20000.0)
		self.assertEqual(flt(rows[1].remaining_amount), 80000.0)
		# last non-cancelled row agrees with the order-level fields
		self.assertEqual(flt(so.pb_billed_amount), 20000.0)
		self.assertEqual(flt(so.pb_remaining_amount), 80000.0)

	def test_no_phantom_paid_amount_on_rounded_invoice(self):
		# 30% of 1495 = 448.50, which ERPNext rounds to an invoice total of
		# 448.00 and computes outstanding_amount against the ROUNDED total
		# (taxes_and_totals.calculate_outstanding_amount). Deriving paid as
		# grand_total - outstanding therefore showed a phantom 0.50 "paid"
		# on a completely unpaid invoice. Paid math must use the same basis
		# ERPNext uses: rounded_total or grand_total.
		so = make_sales_order(
			item_list=[{"item_code": "_Test Item", "qty": 1, "rate": 1495}],
			do_not_submit=True,
		)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.submit()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 30))
		invoice.insert()
		invoice.submit()

		# precondition: rounding actually kicked in for this amount
		self.assertEqual(flt(invoice.grand_total), 448.5)
		self.assertEqual(flt(invoice.rounded_total), 448.0)

		so.reload()
		row = so.pb_progress_billing_log[0]
		self.assertEqual(flt(row.amount_paid), 0.0)
		self.assertEqual(flt(row.payment_percentage), 0.0)

		# the live onload refresh shares the same math
		reloaded_so = frappe.get_doc("Sales Order", so.name)
		reloaded_so.run_method("onload")
		row = reloaded_so.pb_progress_billing_log[0]
		self.assertEqual(flt(row.amount_paid), 0.0)
		self.assertEqual(flt(row.payment_percentage), 0.0)

	def test_progress_no_permanent_across_cancellation(self):
		so = self.make_progress_so()

		invoice_1 = frappe.get_doc(create_progress_invoice(so.name, 10))
		invoice_1.insert()
		invoice_1.submit()

		invoice_2 = frappe.get_doc(create_progress_invoice(so.name, 40))
		invoice_2.insert()
		invoice_2.submit()

		invoice_1.cancel()

		so.reload()
		rows_by_invoice = {row.sales_invoice: row for row in so.pb_progress_billing_log}
		self.assertEqual(rows_by_invoice[invoice_1.name].progress_no, 1)
		self.assertEqual(rows_by_invoice[invoice_1.name].invoice_status, "Cancelled")
		self.assertEqual(rows_by_invoice[invoice_2.name].progress_no, 2)
		self.assertEqual(rows_by_invoice[invoice_2.name].invoice_status, "Submitted")
