# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

"""One-time cleanup for f013 (Bid Approval standalone doctype): removes the old Bid
Approval tab from Quotation on sites that still carry it - the 82 Custom Fields chained
under custom_bid_approval_tab, and the Quotation Bid Approval Workflow they drove.

Fixtures only add and update, they never delete (see erpcloud_itagksa/CLAUDE.md), so a
fixture trim alone cannot remove what a site already has. A fresh site, or one that never
had the tab, has nothing to do here - every field and the workflow are looked up before
being deleted, so re-running this patch (or running it on a site that never had the tab)
is a no-op, not an error.

custom_subcontracted_job is deliberately not in this list: its insert_after
(custom_quote_project_reference) is a separate root outside the tab chain, and the same
fieldname is shared by Work Order, Sales Order and Stock Entry.
"""

import frappe

OLD_TAB_FIELDS = [
	"custom_bid_approval_tab",
	"custom_project_information_section",
	"custom_customer_name2",
	"custom_aramco_9com_code",
	"custom_9com_qualification_status",
	"custom_quality_inspection_level",
	"custom_project_info_column",
	"custom_bid_closing_date",
	"custom_committed_delivery",
	"custom_bid_payment_terms",
	"custom_cost_and_profitability_section",
	"custom_project_cost",
	"custom_total_project_cost",
	"custom_bid_price_section",
	"custom_recommended_selling_price",
	"custom_minimum_negotiation_price",
	"custom_bid_price_column",
	"custom_expected_profit",
	"custom_profit_margin",
	"custom_project_readiness_and_risk",
	"custom_engineering__technical",
	"custom_qaqc__itp__inspection",
	"custom_operations__capacity__delivery",
	"custom_finance__cost__cash_flow",
	"custom_column_break_yykpi",
	"custom_overall_risk",
	"custom_key_conditions__risks",
	"custom_design_review_section",
	"custom_reviewed_by_design",
	"custom_name_design",
	"custom_designation_design",
	"custom_remarks_design",
	"custom_design_review_column",
	"custom_date_design",
	"custom_review_status_design",
	"custom_sign_design_attach",
	"custom_sign_design",
	"custom_manual_sign_design",
	"custom_quality_review_section",
	"custom_reviewed_by_quality",
	"custom_name_quality",
	"custom_designation_quality",
	"custom_remarks_quality",
	"custom_quality_review_column",
	"custom_date_quality",
	"custom_review_status_quality",
	"custom_sign_quality_attach",
	"custom_sign_quality",
	"custom_manual_sign_quality",
	"custom_operations_review_section",
	"custom_reviewed_by_operations",
	"custom_name_operations",
	"custom_designation_operations",
	"custom_remarks_operations",
	"custom_operations_review_column",
	"custom_date_operations",
	"custom_review_status_operations",
	"custom_sign_operations_attach",
	"custom_sign_operations",
	"custom_manual_sign_operations",
	"custom_finance_review_section",
	"custom_reviewed_by_finance",
	"custom_name_finance",
	"custom_designation_finance",
	"custom_remarks_finance",
	"custom_finance_review_column",
	"custom_date_finance",
	"custom_review_status_finance",
	"custom_sign_finance_attach",
	"custom_sign_finance",
	"custom_manual_sign_finance",
	"custom_ceo_review_section",
	"custom_reviewed_by_ceo",
	"custom_name_ceo",
	"custom_designation_ceo",
	"custom_remarks_ceo",
	"custom_ceo_review_column",
	"custom_date_ceo",
	"custom_review_status_ceo",
	"custom_sign_ceo_attach",
	"custom_sign_ceo",
	"custom_manual_sign_ceo",
]

OLD_WORKFLOW = "Quotation Bid Approval"


def execute():
	delete_old_tab_fields()
	delete_old_workflow()
	frappe.db.commit()


def delete_old_tab_fields():
	for fieldname in OLD_TAB_FIELDS:
		name = frappe.db.exists("Custom Field", {"dt": "Quotation", "fieldname": fieldname})
		if name:
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)


def delete_old_workflow():
	if frappe.db.exists("Workflow", OLD_WORKFLOW):
		frappe.delete_doc("Workflow", OLD_WORKFLOW, ignore_permissions=True, force=True)
