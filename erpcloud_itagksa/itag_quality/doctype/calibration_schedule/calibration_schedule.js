// Copyright (c) 2026, ITAG KSA and Contributors
// License: MIT

frappe.ui.form.on("Calibration Schedule", {
	setup(frm) {
		frm.set_query("serial_no", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return { filters: row.item_code ? { item_code: row.item_code } : {} };
		});
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Material Request"),
				() => open_visit_selection(frm),
				__("Create")
			);
		}
	},

	generate_schedule(frm) {
		if (frm.doc.docstatus !== 0) return;
		frm.call("generate_schedule").then(() => frm.refresh_field("schedules"));
	},
});

function open_visit_selection(frm) {
	const pending = (frm.doc.schedules || []).filter((v) => v.completion_status === "Pending");
	if (!pending.length) {
		frappe.msgprint(__("No pending calibration visits to request."));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Select Calibration Visits"),
		fields: [
			{
				fieldname: "visits",
				fieldtype: "MultiCheck",
				label: __("Pending Visits"),
				columns: 1,
				options: pending.map((v) => ({
					label: `${v.serial_no || v.item_code} — ${frappe.datetime.str_to_user(v.scheduled_date)}`,
					value: v.name,
					// Pre-check only visits already due; future visits stay off so one MR
					// doesn't accidentally close a serial's whole calibration plan at once.
					checked: v.scheduled_date <= frappe.datetime.get_today() ? 1 : 0,
				})),
			},
		],
		primary_action_label: __("Create Material Request"),
		primary_action() {
			const selected = dialog.get_value("visits") || [];
			if (!selected.length) {
				frappe.msgprint(__("Select at least one visit."));
				return;
			}
			dialog.hide();
			frappe.xcall(
				"erpcloud_itagksa.itag_quality.doctype.calibration_schedule.calibration_schedule.make_material_request",
				{ source_name: frm.doc.name, visits: JSON.stringify(selected) }
			).then((mr) => {
				const doclist = frappe.model.sync(mr);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			});
		},
	});
	dialog.show();
}
