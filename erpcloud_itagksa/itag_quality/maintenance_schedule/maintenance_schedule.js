// Restrict each row's calibration serial to serials of that row's Item.
frappe.ui.form.on("Maintenance Schedule", {
	setup(frm) {
		frm.set_query("custom_serial_no", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return { filters: row.item_code ? { item_code: row.item_code } : {} };
		});
	},
});
