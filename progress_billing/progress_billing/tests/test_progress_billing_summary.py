import frappe
from frappe.tests.utils import FrappeTestCase
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

from progress_billing.api import create_progress_invoice
from progress_billing.progress_billing.report.progress_billing_summary.progress_billing_summary import execute

# This test site does not have the standard ERPNext test fixtures (_Test Customer,
# _Test Item, _Test Warehouse - _TC, etc.) preloaded. Declaring test_dependencies
# forces frappe's test runner to create them (recursively, via each doctype's
# test_records.json) before this module's tests run. See erpnext's own
# test_sales_order.py for the same idiom (test_dependencies = ["Currency Exchange"]).
test_dependencies = ["Customer", "Item", "Warehouse"]


class TestProgressBillingSummaryReport(FrappeTestCase):
	def test_report_lists_progress_billing_orders_with_correct_rollups(self):
		so = make_sales_order(
			item_list=[{"item_code": "_Test Item", "qty": 1, "rate": 100000}],
			do_not_submit=True,
		)
		so.pb_billing_method = "Progress Billing"
		so.save()
		so.submit()

		invoice = frappe.get_doc(create_progress_invoice(so.name, 25))
		invoice.insert()
		invoice.submit()

		columns, data = execute({"company": so.company})
		row = next((r for r in data if r["sales_order"] == so.name), None)

		self.assertIsNotNone(row)
		self.assertEqual(row["percent_billed"], 25.0)
		self.assertEqual(row["remaining_percent"], 75.0)
		self.assertEqual(row["invoice_count"], 1)
		self.assertEqual(row["status"], "In Progress")

	def test_report_excludes_quantity_based_orders(self):
		so = make_sales_order(do_not_submit=True)
		so.submit()

		columns, data = execute({"company": so.company})
		self.assertIsNone(next((r for r in data if r["sales_order"] == so.name), None))
