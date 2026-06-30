# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

import frappe


QUALITY_VERIFICATION_PRODUCT_TYPES = {"Critical", "Non-Critical"}


def before_save(doc, method=None):
	"""Set custom_quality_verification_required based on item product types.

	Checks if any row in the items table has custom_product_type of
	Critical or Non-Critical. Sets the checkbox accordingly on every save.

	Args:
		doc: Material Request document.
		method (str, optional): Hook method name (unused).
	"""
	doc.custom_quality_verification_required = _has_quality_verification_item(doc.items)


def _has_quality_verification_item(items):
	"""Return 1 if any item requires quality verification, 0 otherwise.

	Args:
		items (list): Material Request Item child rows.

	Returns:
		int: 1 if a Critical or Non-Critical item exists, 0 otherwise.
	"""
	for item in items:
		if item.custom_product_type in QUALITY_VERIFICATION_PRODUCT_TYPES:
			return 1
	return 0
