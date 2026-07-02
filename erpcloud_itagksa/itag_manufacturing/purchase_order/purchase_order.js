frappe.ui.form.on("Purchase Order", {
    refresh(frm) {
        _render_material_issue_button(frm);
        frappe.itagksa.set_collab_serial_query(frm);
    },
});

frappe.ui.form.on("Purchase Order Item", {
    custom_serial_no(frm, cdt, cdn) {
        frappe.itagksa.on_collab_serial_set(frm, cdt, cdn);
    },
    custom_sub_item(frm, cdt, cdn) {
        frappe.itagksa.on_calibration_item_change(frm, cdt, cdn);
    },
});

function _render_material_issue_button(frm) {
    if (!frm.doc.custom_is_collaboration_service_po) return;
    if (frm.doc.docstatus !== 1) return;
    if (frm.doc.custom_collaboration_status === "Fully Issued") return;

    frm.add_custom_button(__("Material Issue"), () => _on_material_issue_click(frm), __("Create"));
}

function _on_material_issue_click(frm) {
    frappe.call({
        method: "erpcloud_itagksa.itag_manufacturing.purchase_order.purchase_order.make_material_issue_se",
        args: { po_name: frm.doc.name },
        freeze: true,
        freeze_message: __("Creating Material Issue..."),
        callback: (r) => {
            if (!r.message) return;
            const doclist = frappe.model.sync(r.message);
            frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
        },
    });
}
