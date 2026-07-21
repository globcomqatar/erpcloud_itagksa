import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice


@frappe.whitelist()
def create_progress_invoice(sales_order: str, percentage: float) -> Document:
	percentage = flt(percentage)
	so = frappe.get_doc("Sales Order", sales_order)

	if so.docstatus != 1:
		frappe.throw(_("Sales Order must be submitted before creating a Progress Invoice."))

	if so.pb_billing_method != "Progress Billing":
		frappe.throw(_("Sales Order {0} is not set to Progress Billing.").format(so.name))

	if percentage <= 0:
		frappe.throw(_("Billing Percentage must be greater than 0."))

	remaining = 100 - flt(so.per_billed)
	if percentage > remaining + 0.01:
		frappe.throw(
			_("Billing Percentage ({0}%) exceeds the remaining {1}% for Sales Order {2}.").format(
				percentage, round(remaining, 2), so.name
			)
		)

	invoice = make_sales_invoice(so.name)

	so_items_by_name = {item.name: item for item in so.items}
	factor = percentage / 100.0

	for item in invoice.items:
		so_item = so_items_by_name.get(item.so_detail)
		if not so_item:
			frappe.throw(
				_("Could not match invoice item {0} back to its Sales Order Item.").format(item.item_code)
			)
		# Restore the full original qty (make_sales_invoice reduces qty by
		# what's already invoiced, which is the wrong model for percentage
		# billing) and scale rate instead, so amount = original_amount * %.
		item.qty = so_item.qty
		item.rate = flt(so_item.rate) * factor
		item.price_list_rate = item.rate
		item.discount_percentage = 0
		item.discount_amount = 0
		item.pricing_rules = ""

	invoice.pb_is_progress_invoice = 1
	invoice.pb_progress_billing_percentage = percentage
	invoice.pb_against_sales_order = so.name
	invoice.calculate_taxes_and_totals()

	# Return the in-memory Document itself rather than invoice.as_dict(): a
	# plain dict's "items" key is shadowed by dict.items() (the built-in
	# method), so callers doing invoice.items on a dict get a bound method,
	# not the child table. frappe.get_doc() already special-cases an
	# incoming BaseDocument (returns it as-is), so this is safe for callers
	# that do frappe.get_doc(create_progress_invoice(...)) too.
	return invoice
