import frappe
from frappe.tests.utils import FrappeTestCase


class TestProgressBillingSummaryPrintFormat(FrappeTestCase):
	def test_print_format_exists_for_sales_order(self):
		meta = frappe.get_doc("Print Format", "Progress Billing Summary")
		self.assertEqual(meta.doc_type, "Sales Order")
		self.assertEqual(meta.print_format_type, "Jinja")
		self.assertIn("pb_progress_billing_log", meta.html)
		# per-row cumulative columns
		self.assertIn("total_billed_amount", meta.html)
		self.assertIn("remaining_amount", meta.html)

	def test_progress_invoice_print_format_exists_for_sales_invoice(self):
		meta = frappe.get_doc("Print Format", "Progress Invoice")
		self.assertEqual(meta.doc_type, "Sales Invoice")
		self.assertEqual(meta.print_format_type, "Jinja")
		# the progress-claim block reads the invoice's stored log row
		self.assertIn("Progress Billing Log", meta.html)
		self.assertIn("total_billed_amount", meta.html)
		self.assertIn("remaining_amount", meta.html)
