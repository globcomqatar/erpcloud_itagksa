import frappe

# erpcloud_itagksa's own "Item Type" custom field (custom_product_type, module ITAG
# Stock) is unconditionally mandatory on Item -- a real, pre-existing business rule
# of this app, unrelated to Progress Billing. ERPNext's own standard test fixtures
# (erpnext/stock/doctype/item/test_records.json, used by make_sales_order and every
# test in this package) don't set it, so the framework's own "_Test Item" family
# fails MandatoryError the moment any test in this app tries to use them.
#
# This runs once, at import time of this test package (before frappe's test runner
# reaches make_test_records_for_doctype), and pre-inserts every one of erpnext's
# standard test Items with custom_product_type filled in. ignore_if_duplicate=True
# makes this safe to run every time (and safe if the site already has some of them).
def _ensure_standard_test_items_satisfy_mandatory_item_type():
	if not frappe.get_meta("Item").has_field("custom_product_type"):
		return

	try:
		records = frappe.get_test_records("Item")
	except (FileNotFoundError, OSError):
		return

	for record in records:
		if frappe.db.exists("Item", record.get("item_code")):
			continue
		doc = frappe.get_doc({**record, "doctype": "Item"})
		if not doc.get("custom_product_type"):
			doc.custom_product_type = "General"
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)

	frappe.db.commit()


_ensure_standard_test_items_satisfy_mandatory_item_type()
