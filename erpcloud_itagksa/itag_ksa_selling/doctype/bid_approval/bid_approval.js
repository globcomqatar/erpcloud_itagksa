// Copyright (c) 2026, ITAG KSA and contributors
// For license information, please see license.txt

// Live cost/profit totals, signature preview, and role-gated review sections. No
// auto-fill of the reviewer - each user opens their own department's section, picks
// themself in Reviewed By, and sets their own review status.

const DEPARTMENT_CONFIG = {
	design: { role: 'Manufacturing Review', signed_statuses: ['Approved', 'Revise'] },
	quality: { role: 'Quality Review', signed_statuses: ['Approved', 'Revise'] },
	operations: { role: 'Operation Review', signed_statuses: ['Approved', 'Revise'] },
	finance: { role: 'Finance Review', signed_statuses: ['Approved', 'Revise'] },
	ceo: { role: 'CEO Approval', signed_statuses: ['Approved', 'Approved with Conditions', 'Revise & Resubmit', 'No Bid'] }
};

const DEPARTMENTS = Object.entries(DEPARTMENT_CONFIG).map(([key, config]) => ({
	role: config.role,
	signed_statuses: config.signed_statuses,
	section: `${key}_review_section`,
	reviewer_field: `reviewed_by_${key}`,
	designation_field: `designation_${key}`,
	status_field: `review_status_${key}`,
	date_field: `date_${key}`,
	signature_attach_field: `sign_${key}_attach`,
	signature_html_field: `sign_${key}`
}));

frappe.ui.form.on('Bid Approval', {
	onload: function (frm) {
		setup_reviews(frm);
	},

	refresh: function (frm) {
		setup_reviews(frm);
	}
});

frappe.ui.form.on('Bid Cost Line', {
	amount: function (frm) {
		calculate_cost_and_profitability(frm);
	},

	project_cost_remove: function (frm) {
		calculate_cost_and_profitability(frm);
	}
});

DEPARTMENTS.forEach((department) => {
	frappe.ui.form.on('Bid Approval', {
		[department.reviewer_field]: function (frm) {
			fetch_employee_designation(frm, department);
		},

		[department.status_field]: function (frm) {
			if (department.signed_statuses.includes(frm.doc[department.status_field])) {
				frm.set_value(department.date_field, frappe.datetime.get_today());
				fetch_employee_signature(frm, department);
			} else {
				frm.set_value(department.date_field, '');
				clear_signature(frm, department);
			}
		}
	});
});

function setup_reviews(frm) {
	set_reviewer_filters(frm);
	set_department_permissions(frm);
	render_all_signatures(frm);
}

function calculate_cost_and_profitability(frm) {
	let total_project_cost = (frm.doc.project_cost || []).reduce(
		(total, row) => total + flt(row.amount),
		0
	);
	let selling_price = flt(frm.doc.recommended_selling_price);
	let expected_profit = selling_price - total_project_cost;

	frm.set_value('total_project_cost', total_project_cost);
	frm.set_value('expected_profit', expected_profit);
	frm.set_value('profit_margin', selling_price ? (expected_profit / selling_price) * 100 : 0);
}

// Dropdown narrows to whoever holds the department role - in practice, just yourself.
function set_reviewer_filters(frm) {
	DEPARTMENTS.forEach((department) => {
		frm.set_query(department.reviewer_field, function () {
			return {
				query: 'frappe.core.doctype.user.user.user_query',
				filters: {
					role: department.role,
					name: frappe.session.user
				}
			};
		});
	});
}

// Only a department's own role (or System Manager) can edit that section's fields.
function set_department_permissions(frm) {
	const section_roles = {};
	DEPARTMENTS.forEach((department) => {
		section_roles[department.section] = [department.role, 'System Manager'];
	});

	let current_roles = null;

	for (let field of frm.fields) {
		if (field.df.fieldtype === 'Section Break') {
			current_roles = section_roles[field.df.fieldname] || null;
			continue;
		}

		if (field.df.fieldtype === 'Column Break' || field.df.read_only === 1) {
			continue;
		}

		if (current_roles) {
			frm.set_df_property(field.df.fieldname, 'read_only', !frappe.user.has_role(current_roles));
		}
	}
}

function fetch_employee_designation(frm, department) {
	let user_id = frm.doc[department.reviewer_field];

	if (!user_id) {
		frm.set_value(department.designation_field, '');
		return;
	}

	frappe.db.get_value('Employee', { user_id: user_id }, 'designation').then((r) => {
		frm.set_value(department.designation_field, (r.message && r.message.designation) || '');
	});
}

function fetch_employee_signature(frm, department) {
	let user_id = frm.doc[department.reviewer_field];

	if (!user_id) {
		clear_signature(frm, department);
		return;
	}

	frappe.db
		.get_value('Employee', { user_id: user_id }, 'custom_attach_sign_image')
		.then((r) => {
			let image_url = r.message && r.message.custom_attach_sign_image;

			if (!image_url) {
				clear_signature(frm, department);
				return;
			}

			frm.set_value(department.signature_attach_field, image_url);
			render_signature(frm, department, image_url);
		});
}

function render_signature(frm, department, image_url) {
	let signature_html = `
		<div style="background-color: #f9f9f9; padding: 30px 20px; margin: 10px 0;">
			<div style="text-align: center;">
				<img src="${image_url}"
					 alt="Signature"
					 style="width: 350px !important; height: 150px !important; display: block !important; margin: 0 auto 10px auto !important; object-fit: contain !important;" />
				<div style="border-top: 2px solid #333; width: 400px; margin: 0 auto; padding-top: 8px;">
					<strong style="font-size: 13px; color: #555; text-transform: uppercase;">Signature</strong>
				</div>
			</div>
		</div>
	`;

	let field = frm.fields_dict[department.signature_html_field];
	if (field && field.$wrapper) {
		field.$wrapper.html(signature_html);
	}
}

function clear_signature(frm, department) {
	let field = frm.fields_dict[department.signature_html_field];
	if (field && field.$wrapper) {
		field.$wrapper.html('');
	}

	if (frm.doc[department.signature_attach_field]) {
		frm.set_value(department.signature_attach_field, '');
	}
}

function render_all_signatures(frm) {
	DEPARTMENTS.forEach((department) => {
		let status = frm.doc[department.status_field];
		if (department.signed_statuses.includes(status) && frm.doc[department.reviewer_field]) {
			fetch_employee_signature(frm, department);
		}
	});
}
