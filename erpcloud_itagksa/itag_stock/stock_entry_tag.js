// Pre-fill a row's Item Tag from its serial numbers on outgoing stock movements
// (issue / transfer). The serials already carry their tags, so the row mirrors them;
// the server handler sync_outgoing_item_tags stays authoritative on save.
frappe.ui.form.on("Stock Entry Detail", {
    serial_no(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.s_warehouse || !row.custom_track_item_tags || !row.serial_no) return;

        frappe.call({
            method: "erpcloud_itagksa.itag_stock.receipt_tag.get_serial_tags",
            args: { serial_nos_text: row.serial_no },
            callback: (r) => {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "custom_item_tag", r.message);
                }
            },
        });
    },
});
