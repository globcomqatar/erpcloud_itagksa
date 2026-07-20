frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		render_progress_billing_summary(frm);
		add_create_progress_invoice_button(frm);
	},
	pb_billing_method(frm) {
		render_progress_billing_summary(frm);
	},
});

function render_progress_billing_summary(frm) {
	if (frm.doc.pb_billing_method !== "Progress Billing") {
		frm.set_df_property("pb_progress_billing_log_html", "options", "");
		return;
	}

	const rows = (frm.doc.pb_progress_billing_log || []).filter(
		(row) => row.invoice_status !== "Cancelled"
	);

	const grand_total = flt(frm.doc.grand_total);
	const total_invoiced = rows.reduce((sum, row) => sum + flt(row.billing_amount), 0);
	const total_received = rows.reduce((sum, row) => sum + flt(row.amount_paid), 0);
	// Sum the rows' live outstanding rather than invoiced - received: invoices
	// with rounded totals owe the rounded amount, so the difference would be
	// off by the rounding adjustments.
	const outstanding = rows.reduce((sum, row) => sum + flt(row.outstanding_amount), 0);
	const per_billed = flt(frm.doc.per_billed);
	const remaining_percent = 100 - per_billed;

	const html = `
		<table class="table table-bordered" style="margin-bottom: 0;">
			<tr><td>${__("Contract Value")}</td><td>${format_currency(grand_total, frm.doc.currency)}</td></tr>
			<tr><td>${__("Total Progress Invoiced")}</td><td>${format_currency(total_invoiced, frm.doc.currency)} (${per_billed.toFixed(2)}%)</td></tr>
			<tr><td>${__("Total Amount Received")}</td><td>${format_currency(total_received, frm.doc.currency)}</td></tr>
			<tr><td>${__("Outstanding Amount")}</td><td>${format_currency(outstanding, frm.doc.currency)}</td></tr>
			<tr><td>${__("Remaining Percentage")}</td><td>${remaining_percent.toFixed(2)}%</td></tr>
		</table>
	`;
	frm.set_df_property("pb_progress_billing_log_html", "options", html);
	frm.refresh_field("pb_progress_billing_log_html");
}

function add_create_progress_invoice_button(frm) {
	if (
		frm.doc.docstatus !== 1 ||
		frm.doc.pb_billing_method !== "Progress Billing" ||
		flt(frm.doc.per_billed) >= 100
	) {
		return;
	}

	frm.add_custom_button(
		__("Create Progress Invoice"),
		() => show_progress_invoice_dialog(frm),
		__("Create")
	);
}

function show_progress_invoice_dialog(frm) {
	const remaining_percent = 100 - flt(frm.doc.per_billed);

	const dialog = new frappe.ui.Dialog({
		title: __("Create Progress Invoice"),
		fields: [
			{
				fieldname: "remaining_percent",
				fieldtype: "Percent",
				label: __("Remaining Percentage"),
				default: remaining_percent,
				read_only: 1,
			},
			{
				fieldname: "percentage",
				fieldtype: "Percent",
				label: __("Billing Percentage"),
				reqd: 1,
			},
		],
		primary_action_label: __("Create Invoice"),
		primary_action(values) {
			if (values.percentage <= 0 || values.percentage > remaining_percent + 0.01) {
				frappe.msgprint(
					__("Billing Percentage must be greater than 0 and not exceed the remaining {0}%.", [
						remaining_percent.toFixed(2),
					])
				);
				return;
			}

			frappe.call({
				method: "progress_billing.api.create_progress_invoice",
				args: {
					sales_order: frm.doc.name,
					percentage: values.percentage,
				},
				freeze: true,
				freeze_message: __("Creating Progress Invoice..."),
				callback(r) {
					if (!r.exc && r.message) {
						dialog.hide();
						frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				},
			});
		},
	});

	dialog.show();
}
