// Copyright (c) 2026, ITAG KSA and Contributors
// License: MIT

frappe.ui.form.on("Quality Inspection", {
	on_submit(frm) {
		// An inward inspection is one serial out of a receipt the inspector is working
		// through, so send them back to it rather than leaving them on a finished
		// inspection. Inspections raised from anywhere else are left alone.
		if (frm.doc.reference_type === "Stock Entry" && frm.doc.reference_name) {
			frappe.set_route("Form", "Stock Entry", frm.doc.reference_name);
		}
	},
});
