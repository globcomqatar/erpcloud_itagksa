// Copyright (c) 2026, ITAG KSA and Contributors
// License: MIT

frappe.query_reports["Calibration Due This Month"] = {
	filters: [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				"January", "February", "March", "April", "May", "June",
				"July", "August", "September", "October", "November", "December",
			].join("\n"),
			default: moment().format("MMMM"),
			reqd: 1,
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Int",
			default: moment().year(),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],

	get_datatable_options(options) {
		return Object.assign(options, { checkboxColumn: true });
	},

	onload(report) {
		report.page.add_inner_button(__("Create Material Request"), () =>
			create_material_requests(report)
		);
	},
};

function create_material_requests(report) {
	const visits = (report.get_checked_items() || []).map((row) => row.visit).filter(Boolean);
	if (!visits.length) {
		frappe.msgprint(__("Tick at least one pending visit first."));
		return;
	}

	frappe.confirm(
		__(
			"Combine the {0} selected visits into a single Material Request? Choose No to raise one per calibration schedule.",
			[visits.length]
		),
		() => raise(report, visits, 1),
		() => raise(report, visits, 0)
	);
}

function raise(report, visits, combined) {
	frappe.xcall(
		"erpcloud_itagksa.itag_quality.doctype.calibration_schedule.calibration_schedule.make_bulk_material_requests",
		{ visits: JSON.stringify(visits), combined }
	).then((names) => {
		if (!names || !names.length) return;
		const links = names
			.map((n) => frappe.utils.get_form_link("Material Request", n, true))
			.join(", ");
		frappe.msgprint({
			title: __("Material Requests Created"),
			message: __("Created {0}: {1}", [names.length, links]),
			indicator: "green",
		});
		report.refresh();
	});
}
