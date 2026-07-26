import frappe

DEAD_ITEM_FIELDS = ("custom_calibration_frequency", "custom_no_of_calibrations")


def execute():
	"""Drop the calibration config that moved from Item onto Calibration Schedule.

	Frequency and count now live on the schedule (purchase date -> end of life,
	spread over a calibration count), so the Item markers and the child table that
	mirrored them are dead. Neither is a fixture, and migrate does not delete a
	doctype dropped from an app, so both need clearing here.
	"""
	for fieldname in DEAD_ITEM_FIELDS:
		frappe.delete_doc_if_exists("Custom Field", f"Item-{fieldname}")

	if frappe.db.exists("DocType", "Calibration Schedule Item"):
		frappe.delete_doc("DocType", "Calibration Schedule Item", force=True)

	frappe.db.commit()
