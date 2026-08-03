// Copyright (c) 2026, ITAG KSA and Contributors
// License: MIT

const INSPECTION_BUTTON = "Create Quality Inspection";

frappe.ui.form.on("Stock Entry", {
	refresh: add_inspection_button,
	custom_inward_inspection_required: add_inspection_button,
});

function add_inspection_button(frm) {
	if (!frm.doc.custom_inward_inspection_required || frm.doc.docstatus === 2) {
		frm.remove_custom_button(__(INSPECTION_BUTTON));
		return;
	}

	// A new or dirty entry holds changes the server cannot see yet, so there is nothing
	// to ask it about the document — only whether this user may inspect at all. The
	// button saves the entry before it creates anything.
	const stock_entry = frm.is_new() || frm.is_dirty() ? null : frm.doc.name;

	// Whether anything is left to inspect, and whether this user is allowed to,
	// are both server-side questions — the button is added once they come back.
	frappe.call({
		method: "erpcloud_itagksa.itag_quality.inward_inspection.may_create_quality_inspections",
		args: { stock_entry },
	}).then((r) => {
		if (r.message && !frm.custom_buttons[__(INSPECTION_BUTTON)]) {
			frm.add_custom_button(__(INSPECTION_BUTTON), () => create_quality_inspections(frm));
		}
	});
}

function create_quality_inspections(frm) {
	// The inspections reference the Stock Entry by name, so unsaved work has to land first
	// — the serials just typed in are what there is to inspect.
	const saved = frm.is_new() || frm.is_dirty() ? frm.save() : Promise.resolve();

	saved
		.then(() =>
			frappe.call({
				method: "erpcloud_itagksa.itag_quality.inward_inspection.create_quality_inspections",
				args: { stock_entry: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating Quality Inspections"),
			})
		)
		.then((r) => {
			const created = r.message || [];
			// Every serial now has an inspection, so the button has nothing left to do.
			frm.refresh();
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
