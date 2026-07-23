// Copyright (c) 2026, ITAG KSA and Contributors
// License: MIT

frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		// The inspections reference the Stock Entry, so it has to exist first; ticking
		// the checkbox dirties the form and the button appears once it is saved.
		if (frm.doc.custom_inward_inspection_required && !frm.is_new() && frm.doc.docstatus < 2) {
			frm.add_custom_button(__("Create Quality Inspection"), () =>
				create_quality_inspections(frm)
			);
		}
	},
});

function create_quality_inspections(frm) {
	frappe.call({
		method: "erpcloud_itagksa.itag_quality.inward_inspection.create_quality_inspections",
		args: { stock_entry: frm.doc.name },
		freeze: true,
		freeze_message: __("Creating Quality Inspections"),
	}).then((r) => {
		const created = r.message || [];
		if (!created.length) {
			frappe.msgprint({
				title: __("Nothing to Create"),
				indicator: "orange",
				message: __("Every serial on this Stock Entry already has a Quality Inspection."),
			});
			return;
		}

		const list_link = `/app/quality-inspection?reference_type=Stock%20Entry&reference_name=${encodeURIComponent(frm.doc.name)}`;
		frappe.msgprint({
			title: __("Quality Inspections Created"),
			indicator: "green",
			message: __("{0} draft Quality Inspections created. <a href='{1}'>Open the list</a>", [
				created.length,
				list_link,
			]),
		});
	});
}
