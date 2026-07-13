frappe.ui.form.on("Purchase Order", {
    onload(frm) {
        _prefill_cash_supplier(frm);
    },
    refresh(frm) {
        _render_material_issue_button(frm);
        frappe.itagksa.set_collab_serial_query(frm);
        _prefill_supplier_store(frm);
    },
    custom_is_collaboration_service_po(frm) {
        _prefill_supplier_store(frm);
    },
});

frappe.ui.form.on("Purchase Order Item", {
    custom_serial_no(frm, cdt, cdn) {
        frappe.itagksa.on_collab_serial_set(frm, cdt, cdn);
    },
});

function _prefill_cash_supplier(frm) {
    // A PO raised from a cash-purchase Material Request opens unsaved with no supplier.
    // Supplier is mandatory, so the save is blocked client-side before the server can
    // fill it — set it here on load, from the source MR carried on the mapped rows.
    if (frm.doc.supplier || frm.doc.docstatus !== 0) {
        return;
    }
    const mr = (frm.doc.items || []).map((row) => row.material_request).find(Boolean);
    if (!mr) {
        return;
    }
    frappe.db
        .get_value("Material Request", mr, ["custom_cash_purchase_request", "custom_cash_supplier"])
        .then((r) => {
            const mrDoc = r.message || {};
            if (mrDoc.custom_cash_purchase_request && mrDoc.custom_cash_supplier && !frm.doc.supplier) {
                frm.set_value("supplier", mrDoc.custom_cash_supplier);
            }
        });
}

function _prefill_supplier_store(frm) {
    if (!frm.doc.custom_is_collaboration_service_po || frm.doc.custom_supplier_store) {
        return;
    }
    frappe.db.get_single_value("ITAG KSA Settings", "default_supplier_store").then((store) => {
        if (store && !frm.doc.custom_supplier_store) {
            frm.set_value("custom_supplier_store", store);
        }
    });
}

function _render_material_issue_button(frm) {
    if (!frm.doc.custom_is_collaboration_service_po) return;
    if (frm.doc.docstatus !== 1) return;

    // Show the button until every sub-item is fully issued — not until the status is
    // "Fully Issued", which returns move past once goods come back.
    frappe.call({
        method: "erpcloud_itagksa.itag_manufacturing.purchase_order.purchase_order.is_fully_issued",
        args: { po_name: frm.doc.name },
        callback: (r) => {
            if (r.message) return;
            frm.add_custom_button(__("Material Issue"), () => _on_material_issue_click(frm), __("Create"));
        },
    });
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
