// Copyright (c) 2026, ITAG KSA and Contributors
// License: MIT

frappe.ui.form.on("Quality Inspection", {
	refresh(frm) {
		if (frm.doc.reference_type !== "Stock Entry") return;

		// The serial is picked when the inspection is raised — one inspection per serial —
		// so both fields are a record of that choice, not something to edit here. Locking
		// item_serial_no also keeps the inspector out of a Link that cannot resolve until
		// the receipt is submitted and the Serial No records exist.
		//
		// Set in refresh rather than onload: quality_itagksa owns this field and clears its
		// options for every reference type other than Job Card, and its onload runs first.
		frm.set_df_property("custom_inward_serial_no", "options", frm.doc.custom_inward_serial_no || "");
		frm.set_df_property("custom_inward_serial_no", "read_only", 1);
		frm.set_df_property("item_serial_no", "read_only", 1);
	},

	on_submit(frm) {
		// An inward inspection is one serial out of a receipt the inspector is working
		// through, so send them back to it rather than leaving them on a finished
		// inspection. Inspections raised from anywhere else are left alone.
		if (frm.doc.reference_type === "Stock Entry" && frm.doc.reference_name) {
			frappe.set_route("Form", "Stock Entry", frm.doc.reference_name);
		}
	},
});
