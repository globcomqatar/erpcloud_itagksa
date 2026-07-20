import frappe
from frappe.tests.utils import FrappeTestCase


class TestCustomFields(FrappeTestCase):
	def test_sales_order_fields_exist(self):
		meta = frappe.get_meta("Sales Order")
		self.assertTrue(meta.has_field("pb_billing_method"))
		self.assertTrue(meta.has_field("pb_progress_billing_status"))
		self.assertTrue(meta.has_field("pb_progress_billing_log_html"))
		self.assertTrue(meta.has_field("pb_progress_billing_log"))
		self.assertFalse(meta.has_field("pb_progress_billing_summary"))

		billing_method_field = meta.get_field("pb_billing_method")
		self.assertEqual(billing_method_field.fieldtype, "Select")
		self.assertEqual(billing_method_field.default, "Quantity Based")
		self.assertEqual(billing_method_field.options, "Quantity Based\nProgress Billing")

		log_field = meta.get_field("pb_progress_billing_log")
		self.assertEqual(log_field.fieldtype, "Table")
		self.assertEqual(log_field.options, "Progress Billing Log")
		self.assertEqual(log_field.allow_on_submit, 1)

		for fieldname in ("pb_total_amount", "pb_billed_amount", "pb_remaining_amount"):
			self.assertTrue(meta.has_field(fieldname))
			field = meta.get_field(fieldname)
			self.assertEqual(field.fieldtype, "Currency")
			self.assertEqual(field.read_only, 1)
			self.assertEqual(field.allow_on_submit, 1)

		self.assertEqual(meta.get_field("pb_total_amount").label, "Total Amount")
		self.assertEqual(meta.get_field("pb_billed_amount").label, "Billed Amount")
		self.assertEqual(meta.get_field("pb_remaining_amount").label, "Remaining Amount")

	def test_sales_invoice_fields_exist(self):
		meta = frappe.get_meta("Sales Invoice")
		self.assertTrue(meta.has_field("pb_is_progress_invoice"))
		self.assertTrue(meta.has_field("pb_progress_billing_percentage"))
		self.assertTrue(meta.has_field("pb_against_sales_order"))

		against_so_field = meta.get_field("pb_against_sales_order")
		self.assertEqual(against_so_field.fieldtype, "Link")
		self.assertEqual(against_so_field.options, "Sales Order")
