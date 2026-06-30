// Copyright (c) 2026, Globcom Manufacturing and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        // Only show button when Sales Order is submitted AND it's a subcontracted order
        if (frm.doc.docstatus === 1 && frm.doc.custom_subcontracted_job
                && frm.doc.custom_grn_status !== 'Fully Received') {
            frm.add_custom_button(__('Good Receipt Note'), function() {
                frappe.model.open_mapped_doc({
                    method: 'erpcloud_itagksa.itag_manufacturing.sales_order.sales_order.create_material_receipt_from_sales_order',
                    frm: frm
                });
            }, __('Create'));
        }

        // NOTE: We do NOT override the standard Work Order button
        // Let ERPNext's standard flow work normally
        // Our server-side validation in work_order.py will catch missing GRN
    }
});
