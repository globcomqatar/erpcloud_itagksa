frappe.provide("frappe.itagksa");

const DELIVERED_STATUS = "Delivered";

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

// When a serial is picked: fill the Calibration Item from the serial if blank,
// and reject a serial that belongs to a different item.
frappe.itagksa.on_collab_serial_set = function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const serial = row.custom_serial_no;
    if (!serial) return;

    frappe.db.get_value("Serial No", serial, "item_code").then((r) => {
        const serial_item = r.message && r.message.item_code;
        if (!serial_item) return;

        if (row.custom_sub_item && row.custom_sub_item !== serial_item) {
            frappe.msgprint({
                title: __("Serial item mismatch"),
                message: __("Serial {0} belongs to {1}, not Calibration Item {2}.", [
                    serial, serial_item, row.custom_sub_item,
                ]),
                indicator: "red",
            });
            frappe.model.set_value(cdt, cdn, "custom_serial_no", "");
            return;
        }
        if (!row.custom_sub_item) {
            frappe.model.set_value(cdt, cdn, "custom_sub_item", serial_item);
        }
    });
};

// Calibration Item changed → drop any serial that no longer matches the filter.
frappe.itagksa.on_calibration_item_change = function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.custom_serial_no) {
        frappe.model.set_value(cdt, cdn, "custom_serial_no", "");
    }
};
