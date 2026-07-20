import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

# This test site does not have the standard ERPNext test fixtures (_Test Customer,
# _Test Item, _Test Warehouse - _TC, etc.) preloaded. Declaring test_dependencies
# forces frappe's test runner to create them (recursively, via each doctype's
# test_records.json) before this module's tests run. See erpnext's own
# test_sales_order.py for the same idiom (test_dependencies = ["Currency Exchange"]).
test_dependencies = ["Customer", "Item", "Warehouse"]


class TestBillingMethodLock(FrappeTestCase):
	def test_billing_method_can_change_before_any_progress_invoice(self):
		so = make_sales_order(do_not_submit=True)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.pb_billing_method = "Quantity Based"
		so.save()  # should not raise
		self.assertEqual(so.pb_billing_method, "Quantity Based")

	def test_billing_method_locked_after_progress_invoice_exists(self):
		so = make_sales_order(item_list=[{"item_code": "_Test Item", "qty": 1, "rate": 1000}], do_not_submit=True)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.submit()

		invoice = frappe.new_doc("Sales Invoice")
		invoice.customer = so.customer
		invoice.company = so.company
		# This site's Global Defaults currency (QAR) differs from "_Test Company"'s
		# native currency (INR, matching its "Debtors - _TC" receivable account).
		# Set it explicitly so party-account-currency validation doesn't reject the
		# insert for a reason unrelated to the billing-method lock under test.
		invoice.currency = so.currency
		invoice.append("items", {"item_code": "_Test Item", "qty": 1, "rate": 100})
		invoice.pb_is_progress_invoice = 1
		invoice.pb_against_sales_order = so.name
		invoice.insert()
		invoice.submit()

		so.reload()
		so.pb_billing_method = "Quantity Based"
		with self.assertRaisesRegex(frappe.ValidationError, "Progress Invoices already exist"):
			so.save()

	def test_onload_refreshes_payment_amounts_from_real_payment(self):
		from progress_billing.api import create_progress_invoice

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

		payment_entry = get_payment_entry(
			"Sales Invoice", invoice.name, party_amount=40000, bank_account="_Test Cash - _TC"
		)
		payment_entry.reference_no = "TEST-REF-001"
		payment_entry.reference_date = invoice.posting_date
		payment_entry.insert()
		payment_entry.submit()

		reloaded_so = frappe.get_doc("Sales Order", so.name)
		# frappe.get_doc() alone does not fire "onload" doc_events - that hook only
		# runs via the Desk UI's document-load path (frappe.desk.form.load.getdoc,
		# which calls doc.run_method("onload") after fetching the doc - see
		# run_onload() in that module). Call it explicitly here to exercise the
		# real hook dispatch mechanism the way a Sales Order form load would.
		reloaded_so.run_method("onload")
		row = reloaded_so.pb_progress_billing_log[0]
		self.assertEqual(round(flt(row.amount_paid), 2), 40000.0)
		self.assertEqual(round(flt(row.outstanding_amount), 2), round(flt(invoice.grand_total) - 40000.0, 2))
		self.assertEqual(round(flt(row.payment_percentage), 2), round(40000.0 / flt(invoice.grand_total) * 100, 2))
