import frappe

OLD_VALUE = "Non-Product"
NEW_VALUE = "General"
FIELDNAME = "custom_product_type"
DOCTYPES = ["Item", "Purchase Order Item", "Purchase Receipt Item", "Material Request Item"]


def execute():
	"""Migrate stored `custom_product_type` values from "Non-Product" to "General".

	The fixture renames the Select option, but that does not rewrite existing row
	values — they keep the old string and show as an invalid option until updated.
	Runs once per site; idempotent (no rows match after the first run).
	"""
	for doctype in DOCTYPES:
		if not frappe.db.has_column(doctype, FIELDNAME):
			continue
		table = f"tab{doctype}"
		frappe.db.sql(
			f"update `{table}` set {FIELDNAME} = %s where {FIELDNAME} = %s",
			(NEW_VALUE, OLD_VALUE),
		)
	frappe.db.commit()
