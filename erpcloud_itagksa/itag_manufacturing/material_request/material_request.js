frappe.ui.form.on("Material Request", {
    refresh(frm) {
        frappe.itagksa.set_collab_serial_query(frm);
        prefill_supplier_store(frm);
    },
    custom_is_collaboration_service_po(frm) {
        prefill_supplier_store(frm);
    },
});

frappe.ui.form.on("Material Request Item", {
    custom_serial_no(frm, cdt, cdn) {
        frappe.itagksa.on_collab_serial_set(frm, cdt, cdn);
    },
});

function prefill_supplier_store(frm) {
    if (!frm.doc.custom_is_collaboration_service_po || frm.doc.custom_supplier_store) {
        return;
    }
    frappe.db.get_single_value("ITAG KSA Settings", "default_supplier_store").then((store) => {
        if (store && !frm.doc.custom_supplier_store) {
            frm.set_value("custom_supplier_store", store);
        }
    });
}
