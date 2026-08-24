# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def create_bid_approval(quotation):
	quotation_doc = frappe.get_doc("Quotation", quotation)
	quotation_doc.check_permission("read")

	if quotation_doc.docstatus != 0:
		frappe.throw(_("Bid Approval can only be created from a draft Quotation."))

	if frappe.db.exists("Bid Approval", {"quotation": quotation_doc.name}):
		frappe.throw(_("A Bid Approval already exists for this Quotation."))

	bid_approval = frappe.new_doc("Bid Approval")
	bid_approval.quotation = quotation_doc.name
	bid_approval.customer = quotation_doc.customer_name
	bid_approval.subcontracted_job = quotation_doc.custom_subcontracted_job
	bid_approval.recommended_selling_price = flt(quotation_doc.rounded_total) or flt(
		quotation_doc.grand_total
	)
	bid_approval.insert()

	return bid_approval.name
