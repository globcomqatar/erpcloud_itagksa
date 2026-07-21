import frappe
from frappe.tests.utils import FrappeTestCase


class TestProgressBillingLogDoctype(FrappeTestCase):
	def test_doctype_exists_with_expected_fields(self):
		meta = frappe.get_meta("Progress Billing Log")
		self.assertTrue(meta.istable)

		expected_fields = {
			"progress_no": "Int",
			"billing_date": "Date",
			"billing_percentage": "Percent",
			"billing_amount": "Currency",
			"sales_invoice": "Link",
			"invoice_status": "Select",
			"amount_paid": "Currency",
			"outstanding_amount": "Currency",
			"payment_percentage": "Percent",
			"remarks": "Small Text",
		}
		for fieldname, fieldtype in expected_fields.items():
			field = meta.get_field(fieldname)
			self.assertIsNotNone(field, f"missing field {fieldname}")
			self.assertEqual(field.fieldtype, fieldtype)

		for fieldname in ("invoice_status", "amount_paid", "outstanding_amount", "payment_percentage", "remarks"):
			self.assertEqual(
				meta.get_field(fieldname).allow_on_submit, 1, f"{fieldname} should allow_on_submit"
			)

	def test_sales_invoice_link_options(self):
		meta = frappe.get_meta("Progress Billing Log")
		self.assertEqual(meta.get_field("sales_invoice").options, "Sales Invoice")
