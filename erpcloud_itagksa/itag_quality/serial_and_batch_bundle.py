# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

from erpcloud_itagksa.itag_quality.serial_no.serial_no import generate_calibration_schedule


def on_submit(doc, method=None):
	"""Generate calibration schedules for serials created by a stock receipt.

	Stock-transaction serials are bulk-inserted (bypassing Serial No ORM hooks),
	so the Serial and Batch Bundle is the reliable trigger: on an inward bundle
	every listed serial exists by submit time. generate_calibration_schedule is
	idempotent and no-ops for non-calibration items, so processing every inward
	entry is safe.
	"""
	if doc.type_of_transaction != "Inward":
		return

	for entry in doc.entries:
		if entry.serial_no:
			generate_calibration_schedule(entry.serial_no, doc.item_code)
