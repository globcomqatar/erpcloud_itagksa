import frappe


def propagate_bom_from_routing(doc, method=None):
    """Copy custom_acceptance_criteria from Routing Operation → BOM Operation rows.

    Runs after ERPNext's BOM.validate() which already populated doc.operations
    from the routing. We match by operation name to fill in the custom field.
    """
    if not doc.get("routing") or not doc.get("operations"):
        return

    try:
        routing_doc = frappe.get_doc("Routing", doc.routing)
        routing_map = {
            row.operation: row.get("custom_acceptance_criteria") or ""
            for row in routing_doc.operations
        }

        for op_row in doc.operations:
            if op_row.operation in routing_map:
                op_row.custom_acceptance_criteria = routing_map[op_row.operation]

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="BOM: Acceptance Criteria Propagation Error"
        )


def propagate_wo_from_bom(doc, method=None):
    """Copy custom_acceptance_criteria from BOM Operation → Work Order Operation rows.

    Runs after ERPNext's Work Order validate() which already populated
    doc.operations from the BOM. We match by operation name.
    """
    if not doc.get("bom_no") or not doc.get("operations"):
        return

    try:
        bom_ops = frappe.get_all(
            "BOM Operation",
            filters={"parent": doc.bom_no},
            fields=["operation", "custom_acceptance_criteria"],
        )
        bom_map = {
            row.operation: row.get("custom_acceptance_criteria") or ""
            for row in bom_ops
        }

        for op_row in doc.operations:
            if op_row.operation in bom_map:
                op_row.custom_acceptance_criteria = bom_map[op_row.operation]

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="Work Order: Acceptance Criteria Propagation Error"
        )


def propagate_job_card_from_wo(doc):
    """Copy custom_acceptance_criteria from Work Order Operation → Job Card.

    Called from job_card.before_save. Matches by operation + sequence_id.
    Returns early if work_order or operation not set.
    """
    if not doc.get("work_order") or not doc.get("operation"):
        return

    try:
        work_order = frappe.get_doc("Work Order", doc.work_order)
        for row in work_order.operations:
            if row.operation == doc.operation and row.sequence_id == doc.sequence_id:
                doc.custom_operation_description = row.description or ""
                doc.custom_inspection_required = row.custom_quality_inspection_required
                doc.custom_acceptance_criteria = row.custom_acceptance_criteria or ""
                break

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="Job Card: Acceptance Criteria Propagation Error"
        )
