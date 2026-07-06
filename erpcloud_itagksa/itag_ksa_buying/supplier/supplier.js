// Copyright (c) 2026, ITAG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier', {
	refresh: function (frm) {
		frappe.db.get_single_value('ITAG KSA Settings', 'reevaluation_role').then((role) => {
			const allowed = !role || (frappe.user_roles || []).includes(role);
			frm.set_df_property('custom_supplier_approval', 'hidden', allowed ? 0 : 1);
		});
	},
});
