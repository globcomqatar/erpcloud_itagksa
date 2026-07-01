// Copyright (c) 2026, Globcom Manufacturing and contributors
// For license information, please see license.txt

/**
 * Stock Entry Client Script
 *
 * Auto-fetches heat_no, heat_lot_no, drawing_no, and part_no from Serial No master
 * when user enters serial numbers in Stock Entry Detail items.
 */

const MATERIAL_RECEIPT_CPI = 'Material Receipt - CPI';

frappe.ui.form.on('Stock Entry', {
    refresh: function(frm) {
        apply_cpi_default_warehouse(frm);

        // Re-apply lock on form load for CPI checkboxes
        if (frm.doc.custom_customer_property_grn || frm.doc.custom_customer_property_return) {
            frm.set_df_property('stock_entry_type', 'read_only', 1);
        } else {
            frm.set_df_property('stock_entry_type', 'read_only', 0);
        }
        if (frm.doc.custom_customer_property_grn) {
            frm.set_value('custom_subcontracted_job', 1);
        }

        // Show subcontract workflow buttons on submitted subcontracted entries with no SO linked

        if (frm.doc.docstatus === 1 &&
            frm.doc.custom_subcontracted_job &&
            !frm.doc.custom_customer_sales_order_number) {

            frm.add_custom_button(__('Sales Order'), function() {
                create_sales_order_from_stock_entry(frm);
            }, __('Create'));
        }
    },

    stock_entry_type: function(frm) {
        // When the type becomes a CPI receipt (button or checkbox), pre-fill the
        // default target warehouse so the user sees it before saving.
        apply_cpi_default_warehouse(frm);
    },

    custom_customer_property_grn: function(frm) {
        if (frm.doc.custom_customer_property_grn) {
            frm.set_value('stock_entry_type', 'Material Receipt - CPI');
            frm.set_value('custom_subcontracted_job', 1);
            frm.set_df_property('stock_entry_type', 'read_only', 1);
        } else {
            frm.set_value('stock_entry_type', '');
            frm.set_value('custom_subcontracted_job', 0);
            frm.set_df_property('stock_entry_type', 'read_only', 0);
        }
    },

    custom_customer_property_return: function(frm) {
        if (frm.doc.custom_customer_property_return) {
            frm.set_value('stock_entry_type', 'Material Return - CPI');
            frm.set_df_property('stock_entry_type', 'read_only', 1);
        } else {
            frm.set_value('stock_entry_type', '');
            frm.set_df_property('stock_entry_type', 'read_only', 0);
        }
    }
});

frappe.ui.form.on('Stock Entry Detail', {
    items_add: function(frm, cdt, cdn) {
        // Fill a newly added row's target warehouse with the cached CPI default.
        if (frm.doc.stock_entry_type !== MATERIAL_RECEIPT_CPI) {
            return;
        }
        if (!frm.__cpi_default_warehouse) {
            return;
        }
        const row = locals[cdt][cdn];
        if (!row.t_warehouse) {
            frappe.model.set_value(cdt, cdn, 't_warehouse', frm.__cpi_default_warehouse);
        }
    },

    serial_no: function(frm, cdt, cdn) {
        // Get the current row
        let row = locals[cdt][cdn];

        // CRITICAL: Only auto-fetch for subcontracted orders
        if (!frm.doc.custom_subcontracted_job) {
            return;  // Skip auto-fetch if not a subcontracted order
        }

        // Only auto-fetch for specific purposes where serial numbers already exist
        const allowed_purposes = [
            'Material Transfer',
            'Material Issue',
            'Material Transfer for Manufacture'
        ];

        if (!allowed_purposes.includes(frm.doc.purpose)) {
            return;  // Skip auto-fetch for other purposes
        }

        // Only auto-fetch if serial_no is entered
        if (row.serial_no) {
            auto_fetch_serial_attributes(frm, row);
        } else {
            // Clear custom fields if serial_no is cleared
            frappe.model.set_value(cdt, cdn, 'custom_heat_no', '');
            frappe.model.set_value(cdt, cdn, 'custom_heat_lot_no', '');
            frappe.model.set_value(cdt, cdn, 'custom_drawing_no', '');
            frappe.model.set_value(cdt, cdn, 'custom_part_no', '');
        }
    },

    serial_and_batch_bundle: function(frm, cdt, cdn) {
        // CRITICAL: Only auto-fetch for subcontracted orders
        if (!frm.doc.custom_subcontracted_job) {
            return;  // Skip auto-fetch if not a subcontracted order
        }

        // Only auto-fetch for specific purposes where serial numbers already exist
        const allowed_purposes = [
            'Material Transfer',
            'Material Issue',
            'Material Transfer for Manufacture'
        ];

        if (!allowed_purposes.includes(frm.doc.purpose)) {
            return;  // Skip auto-fetch for other purposes
        }

        // Also trigger on serial_and_batch_bundle change (ERPNext 15+)
        let row = locals[cdt][cdn];

        if (row.serial_and_batch_bundle) {
            // Fetch serial numbers from bundle and auto-populate attributes
            fetch_serials_from_bundle(frm, row);
        }
    }
});


/**
 * Pre-fill the default target warehouse on a draft CPI Material Receipt so the
 * user sees it before saving. Reads default_target_warehouse from ITAG KSA
 * Settings, sets the header to_warehouse and any empty item t_warehouse, and
 * shows a notice. The server before_validate handler remains the authority on
 * save; this is display only. Skips when the user already chose a warehouse.
 */
function apply_cpi_default_warehouse(frm) {
    if (frm.doc.docstatus !== 0) {
        return;  // draft only
    }
    if (frm.doc.stock_entry_type !== MATERIAL_RECEIPT_CPI) {
        return;
    }

    frappe.db.get_single_value('ITAG KSA Settings', 'default_target_warehouse').then(warehouse => {
        if (!warehouse) {
            return;
        }
        frm.__cpi_default_warehouse = warehouse;

        let filled = false;
        if (!frm.doc.to_warehouse) {
            frm.set_value('to_warehouse', warehouse);
            filled = true;
        }
        (frm.doc.items || []).forEach(row => {
            if (!row.t_warehouse) {
                frappe.model.set_value(row.doctype, row.name, 't_warehouse', warehouse);
                filled = true;
            }
        });

        if (filled) {
            frm.refresh_field('items');
            frappe.show_alert({
                message: __('Target warehouse auto-filled from ITAG KSA Settings: {0}', [warehouse]),
                indicator: 'blue'
            }, 5);
        }
    });
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
            serial_nos_string: row.serial_no
        },
        callback: function(r) {
            frappe.dom.unfreeze();

            if (r.message) {
                let data = r.message;

                // Convert arrays to newline-separated strings
                let heat_nos_string = data.heat_nos.join('\n');
                let heat_lot_nos_string = data.heat_lot_nos.join('\n');
                let drawing_nos_string = data.drawing_nos.join('\n');
                let part_nos_string = data.part_nos.join('\n');

                // Update the row fields
                frappe.model.set_value(row.doctype, row.name, 'custom_heat_no', heat_nos_string);
                frappe.model.set_value(row.doctype, row.name, 'custom_heat_lot_no', heat_lot_nos_string);
                frappe.model.set_value(row.doctype, row.name, 'custom_drawing_no', drawing_nos_string);
                frappe.model.set_value(row.doctype, row.name, 'custom_part_no', part_nos_string);

                // Show success message if attributes were found
                if (heat_nos_string || heat_lot_nos_string || drawing_nos_string || part_nos_string) {
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


/**
 * Fetch serial numbers from Serial and Batch Bundle
 * (For ERPNext version 15+ compatibility)
 */
function fetch_serials_from_bundle(frm, row) {
    if (!row.serial_and_batch_bundle) {
        return;
    }

    // Fetch serial numbers from the bundle
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Serial and Batch Bundle',
            name: row.serial_and_batch_bundle
        },
        callback: function(r) {
            if (r.message && r.message.entries) {
                // Extract serial numbers from bundle entries
                let serial_nos = r.message.entries
                    .filter(entry => entry.serial_no)
                    .map(entry => entry.serial_no);

                if (serial_nos.length > 0) {
                    // Convert to string and fetch attributes
                    let serial_nos_string = serial_nos.join('\n');

                    // Create a temporary row object with serial_no for fetching
                    let temp_row = Object.assign({}, row);
                    temp_row.serial_no = serial_nos_string;

                    auto_fetch_serial_attributes(frm, temp_row);
                }
            }
        }
    });
}


/**
 * Create a draft Sales Order from Stock Entry for billing.
 * Saves the SO server-side and links it back to this Stock Entry.
 */
function create_sales_order_from_stock_entry(frm) {
    frappe.call({
        method: 'erpcloud_itagksa.itag_manufacturing.stock_entry.stock_entry.create_sales_order_from_stock_entry',
        args: { stock_entry_name: frm.doc.name },
        freeze: true,
        freeze_message: __('Creating Sales Order...'),
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Sales Order {0} created.', [r.message]),
                    indicator: 'green'
                }, 5);
                frm.reload_doc();
                frappe.set_route('Form', 'Sales Order', r.message);
            }
        }
    });
}


