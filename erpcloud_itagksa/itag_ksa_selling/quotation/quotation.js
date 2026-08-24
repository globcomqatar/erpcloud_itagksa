// Copyright (c) 2026, ITAG KSA and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quotation', {
	refresh: function (frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(
				__('Bid Approval'),
				function () {
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
				},
				__('Create')
			);
		}
	}
});
