// Copyright (c) 2026, ITAG KSA and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quotation', {
	refresh: function (frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frappe.db.get_value('Bid Approval', { quotation: frm.doc.name }, 'name').then((r) => {
				let existing = r.message && r.message.name;

				if (existing) {
					frm.add_custom_button(__('Bid Approval'), function () {
						frappe.set_route('Form', 'Bid Approval', existing);
					});
				} else {
					frm.add_custom_button(__('Bid Approval'), function () {
						frappe.call({
							method: 'erpcloud_itagksa.itag_ksa_selling.quotation.quotation.create_bid_approval',
							args: { quotation: frm.doc.name },
							freeze: true,
							callback: function (r) {
								if (r.message) {
									frappe.set_route('Form', 'Bid Approval', r.message);
								}
							}
						});
					});
				}
			});
		}
	}
});
