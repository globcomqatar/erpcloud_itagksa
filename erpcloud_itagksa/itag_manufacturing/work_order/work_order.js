// Copyright (c) 2026, Globcom Manufacturing and contributors
// For license information, please see license.txt

/**
 * Work Order Client Script
 *
 * Features:
 * - Auto-fetches heat_no, drawing_no, and part_no from Serial No master
 * - Populates parent custom_serial_no field with options from required_items
 */

frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
        // Populate serial number options from required_items
        populate_serial_no_options(frm);
    },

    required_items_add: function(frm) {
        // Refresh serial number options when items are added
        populate_serial_no_options(frm);
    },

    required_items_remove: function(frm) {
        // Refresh serial number options when items are removed
        populate_serial_no_options(frm);
    }
});

frappe.ui.form.on('Work Order Item', {
    custom_serial_no: function(frm, cdt, cdn) {
        // Get the current row
        let row = locals[cdt][cdn];

        // Only auto-fetch if custom_serial_no is entered
        if (row.custom_serial_no) {
            auto_fetch_serial_attributes(frm, row);
        } else {
            // Clear custom fields if custom_serial_no is cleared
            frappe.model.set_value(cdt, cdn, 'custom_heat_no', '');
            frappe.model.set_value(cdt, cdn, 'custom_drawing_no', '');
            frappe.model.set_value(cdt, cdn, 'custom_part_no', '');
        }

        // Update parent field options when child serial number changes
        populate_serial_no_options(frm);
    }
});


/**
 * Populate parent custom_serial_no field with options from required_items child table
 */
function populate_serial_no_options(frm) {
    if (!frm.doc.required_items || frm.doc.required_items.length === 0) {
        // No items - clear options
        frm.set_df_property('custom_serial_no', 'options', '');
        return;
    }

    // Collect unique serial numbers from required_items
    let serial_numbers = new Set();

    frm.doc.required_items.forEach(function(item) {
        if (item.custom_serial_no) {
            // Split by newline or comma to handle multiple serials
            let serials = item.custom_serial_no.split(/[\n,]+/).map(s => s.trim()).filter(s => s);
            serials.forEach(serial => serial_numbers.add(serial));
        }
    });

    // Convert Set to sorted array
    let options_array = Array.from(serial_numbers).sort();

    // Set as options for the parent field (newline-separated)
    let options_string = options_array.join('\n');
    frm.set_df_property('custom_serial_no', 'options', options_string);

    // AUTO-POPULATE: If only 1 serial number, auto-select it (UX improvement)
    // Use direct assignment instead of frm.set_value() to avoid marking the
    // form dirty on post-save refresh. The value is displayed immediately and
    // persisted on the user's next save.
    if (options_array.length === 1 && !frm.doc.custom_serial_no) {
        frm.doc.custom_serial_no = options_array[0];
        frm.refresh_field('custom_serial_no');
        frappe.show_alert({
            message: __('Serial number auto-selected: {0}', [options_array[0]]),
            indicator: 'blue'
        }, 3);
    }

    // Refresh the field to show updated options
    frm.refresh_field('custom_serial_no');
}


/**
 * Auto-fetch serial attributes from Serial No master
 */
function auto_fetch_serial_attributes(frm, row) {
    // Show loading indicator
    frappe.dom.freeze(__('Fetching serial attributes...'));

    // Call server-side method to fetch attributes
    frappe.call({
        method: 'erpcloud_itagksa.itag_manufacturing.utils.serial_field_utils.fetch_serial_attributes_from_master',
        args: {
            serial_nos_string: row.custom_serial_no
        },
        callback: function(r) {
            frappe.dom.unfreeze();

            if (r.message) {
                let data = r.message;

                // Convert arrays to newline-separated strings
                let heat_nos_string = data.heat_nos.join('\n');
                let drawing_nos_string = data.drawing_nos.join('\n');
                let part_nos_string = data.part_nos.join('\n');

                // Update the row fields
                frappe.model.set_value(row.doctype, row.name, 'custom_heat_no', heat_nos_string);
                frappe.model.set_value(row.doctype, row.name, 'custom_drawing_no', drawing_nos_string);
                frappe.model.set_value(row.doctype, row.name, 'custom_part_no', part_nos_string);

                // Show success message if attributes were found
                if (heat_nos_string || drawing_nos_string || part_nos_string) {
                    frappe.show_alert({
                        message: __('Serial attributes auto-populated'),
                        indicator: 'green'
                    }, 3);
                } else {
                    // Show info message if no attributes found
                    frappe.show_alert({
                        message: __('No attributes found for these serial numbers'),
                        indicator: 'orange'
                    }, 3);
                }
            }
        },
        error: function(r) {
            frappe.dom.unfreeze();
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to fetch serial attributes. Please check the serial numbers.'),
                indicator: 'red'
            });
        }
    });
}
