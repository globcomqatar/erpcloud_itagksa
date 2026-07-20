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


class TestCreateProgressInvoice(FrappeTestCase):
	def make_progress_so(self):
		so = make_sales_order(
			item_list=[
				{"item_code": "_Test Item", "qty": 1, "rate": 40000},
				{"item_code": "_Test Item", "qty": 1, "rate": 35000},
				{"item_code": "_Test Item", "qty": 1, "rate": 25000},
			],
			do_not_submit=True,
		)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.submit()
		return so

	def test_rejects_zero_or_negative_percentage(self):
		so = self.make_progress_so()
		self.assertRaises(frappe.ValidationError, create_progress_invoice, so.name, 0)
		self.assertRaises(frappe.ValidationError, create_progress_invoice, so.name, -5)

	def test_rejects_percentage_above_remaining(self):
		so = self.make_progress_so()
		self.assertRaises(frappe.ValidationError, create_progress_invoice, so.name, 101)

	def test_rejects_when_not_progress_billing(self):
		so = make_sales_order(do_not_submit=True)
		so.submit()
		self.assertRaises(frappe.ValidationError, create_progress_invoice, so.name, 10)

	def test_generates_scaled_line_amounts(self):
		so = self.make_progress_so()
		invoice = create_progress_invoice(so.name, 10)
		self.assertEqual(len(invoice.items), 3)
		amounts = sorted(round(flt(item.amount), 2) for item in invoice.items)
		self.assertEqual(amounts, [2500.0, 3500.0, 4000.0])
		self.assertEqual(round(flt(invoice.pb_progress_billing_percentage), 2), 10.0)
		self.assertEqual(invoice.pb_against_sales_order, so.name)
		self.assertEqual(invoice.pb_is_progress_invoice, 1)
		self.assertEqual([item.qty for item in invoice.items], [1, 1, 1])

	def test_cumulative_billing_reaches_100_percent(self):
		so = self.make_progress_so()

		inv1 = frappe.get_doc(create_progress_invoice(so.name, 10))
		inv1.insert()
		inv1.submit()

		inv2 = frappe.get_doc(create_progress_invoice(so.name, 40))
		inv2.insert()
		inv2.submit()

		inv3 = frappe.get_doc(create_progress_invoice(so.name, 50))
		inv3.insert()
		inv3.submit()

		so.reload()
		self.assertAlmostEqual(flt(so.per_billed), 100.0, delta=0.1)

	def test_native_over_billing_guard_blocks_stale_draft(self):
		so = self.make_progress_so()

		# Two drafts created back-to-back, both valid at creation time
		# (per_billed is still 0 for both reads).
		stale_invoice = frappe.get_doc(create_progress_invoice(so.name, 60))
		stale_invoice.insert()

		other_invoice = frappe.get_doc(create_progress_invoice(so.name, 60))
		other_invoice.insert()
		other_invoice.submit()

		# Submitting the stale draft now would push the order to 120% billed.
		# Only ERPNext's native check_overflow_with_allowance guard (no
		# custom code in this app) can catch this, since our own percentage
		# check already passed back when the draft was created.
		#
		# ERPNext's update_prevdoc_status() writes the Sales Order's new
		# per_billed *before* validate_qty() raises the overflow error (see
		# controllers/status_updater.py: update_prevdoc_status = update_qty()
		# then validate_qty()). In production this stray write is undone
		# automatically because any exception during a whitelisted call
		# ends the HTTP request with frappe.db.rollback() (frappe/app.py).
		# A direct .submit() in-process doesn't get that request-boundary
		# rollback, so we simulate it with an explicit savepoint here.
		save_point = "test_native_over_billing_guard"
		frappe.db.savepoint(save_point)
		with self.assertRaises(frappe.ValidationError):
			try:
				stale_invoice.submit()
			except Exception:
				frappe.db.rollback(save_point=save_point)
				raise

		so.reload()
		self.assertAlmostEqual(flt(so.per_billed), 60.0, delta=0.1)
