frappe.provide("frappe.itagksa");

const DELIVERED_STATUS = "Delivered";

// Show the serial's Item Tag inline ("SN: Tag") in the collab Serial No link fields.
// Reads the read-only custom_serial_no_tag fetch field on the row; scoped to the two
// collab child tables so Serial No links elsewhere are untouched.
frappe.form.link_formatters["Serial No"] = function (value, doc) {
    if (
        doc &&
        doc.custom_serial_no_tag &&
        ["Material Request Item", "Purchase Order Item"].includes(doc.doctype)
    ) {
        return `${value}: ${doc.custom_serial_no_tag}`;
    }
    return value;
};

// Restrict the row's Serial No link to serials of the selected Calibration Item,
// and hide serials already delivered out.
frappe.itagksa.set_collab_serial_query = function (frm) {
    frm.set_query("custom_serial_no", "items", (doc, cdt, cdn) => {
        const row = locals[cdt][cdn];
        const filters = { status: ["!=", DELIVERED_STATUS] };
        if (row.custom_sub_item) {
            filters.item_code = row.custom_sub_item;
        }
        return { filters };
    });
};

// When a serial is picked and the Calibration Item is still blank, fill it from the
// serial. The serial itself is never auto-cleared — any item/serial mismatch is left
// to server-side validation on save.
frappe.itagksa.on_collab_serial_set = function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.custom_serial_no || row.custom_sub_item) return;

    frappe.db.get_value("Serial No", row.custom_serial_no, "item_code").then((r) => {
        const serial_item = r.message && r.message.item_code;
        if (serial_item) {
            frappe.model.set_value(cdt, cdn, "custom_sub_item", serial_item);
        }
    });
};
