frappe.ui.form.on("Stock Entry", {
    refresh(frm) {
        _render_create_grn_button(frm);
        _apply_stock_entry_type_lock(frm);
        _apply_purchase_order_lock(frm);
    },

    custom_is_collaboration_delivery_note(frm) {
        if (frm.doc.custom_is_collaboration_delivery_note) {
            if (frm.doc.custom_is_collaboration_grn) {
                frm.set_value("custom_is_collaboration_grn", 0);
            }
            frm.set_value("stock_entry_type", "Material Issue to Supplier");
        } else if (!frm.doc.custom_is_collaboration_grn) {
            frm.set_value("stock_entry_type", "");
        }
        _apply_stock_entry_type_lock(frm);
    },

    custom_is_collaboration_grn(frm) {
        if (frm.doc.custom_is_collaboration_grn) {
            if (frm.doc.custom_is_collaboration_delivery_note) {
                frm.set_value("custom_is_collaboration_delivery_note", 0);
            }
            frm.set_value("stock_entry_type", "Material Receipt from Supplier");
        } else if (!frm.doc.custom_is_collaboration_delivery_note) {
            frm.set_value("stock_entry_type", "");
        }
        _apply_stock_entry_type_lock(frm);
    },

    custom_purchase_order(frm) {
        _apply_purchase_order_lock(frm);
        if (frm.doc.docstatus !== 0) return;
        if (!frm.doc.custom_is_collaboration_delivery_note) return;
        if (!frm.doc.custom_purchase_order) return;

        frappe.call({
            method: "erpcloud_itagksa.itag_manufacturing.stock_entry.collab_stock_entry.pull_from_po",
            args: { po_name: frm.doc.custom_purchase_order },
            freeze: true,
            freeze_message: __("Loading PO sub-items..."),
            callback: (r) => {
                if (r.message) _apply_pulled_po_data(frm, r.message);
            },
        });
    },
});

function _apply_purchase_order_lock(frm) {
    const locked = !!frm.doc.custom_purchase_order;
    frm.set_df_property("custom_purchase_order", "read_only", locked ? 1 : 0);
    frm.refresh_field("custom_purchase_order");
}

function _apply_stock_entry_type_lock(frm) {
    const locked = !!(frm.doc.custom_is_collaboration_delivery_note || frm.doc.custom_is_collaboration_grn);
    frm.set_df_property("stock_entry_type", "read_only", locked ? 1 : 0);
    frm.refresh_field("stock_entry_type");
}

function _render_create_grn_button(frm) {
    if (frm.doc.docstatus !== 1) return;
    if (!frm.doc.custom_is_collaboration_delivery_note) return;

    frm.add_custom_button(__("Create GRN"), () => _on_create_grn_click(frm));
}

function _on_create_grn_click(frm) {
    frappe.model.open_mapped_doc({
        method: "erpcloud_itagksa.itag_manufacturing.stock_entry.collab_stock_entry.make_grn_from_issue",
        frm: frm,
    });
}

function _apply_pulled_po_data(frm, payload) {
    frm.clear_table("items");
    (payload.items || []).forEach((row) => {
        const child = frm.add_child("items");
        Object.assign(child, row);
    });
    frm.set_value("custom_supplier", payload.supplier || "");
    frm.set_value("custom_supplier_name", payload.supplier_name || "");
    if (payload.target_warehouse) {
        frm.set_value("to_warehouse", payload.target_warehouse);
    }
    frm.refresh_field("items");
}
