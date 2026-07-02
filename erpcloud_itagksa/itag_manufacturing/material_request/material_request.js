frappe.ui.form.on("Material Request", {
    refresh(frm) {
        frappe.itagksa.set_collab_serial_query(frm);
    },
});

frappe.ui.form.on("Material Request Item", {
    custom_serial_no(frm, cdt, cdn) {
        frappe.itagksa.on_collab_serial_set(frm, cdt, cdn);
    },
    custom_sub_item(frm, cdt, cdn) {
        frappe.itagksa.on_calibration_item_change(frm, cdt, cdn);
    },
});
