app_name = "progress_billing"
app_title = "Progress Billing"
app_publisher = "Globcom Qatar"
app_description = "Percentage-of-contract-value progress invoicing for ERPNext Sales Orders"
app_email = "waheed@globcomqatar.com"
app_license = "mit"

required_apps = ["erpnext"]

# Includes in <head>
# ------------------

doctype_js = {
	"Sales Order": "public/js/sales_order.js",
}

# Installation
# ------------

after_install = "progress_billing.install.after_install"

# Migration
# ---------

after_migrate = "progress_billing.setup.custom_fields.sync_custom_fields"

# Document Events
# ---------------

doc_events = {
	"Sales Order": {
		"onload": "progress_billing.overrides.sales_order.refresh_progress_billing_log_payments",
		"validate": "progress_billing.overrides.sales_order.validate_billing_method_lock",
		"before_update_after_submit": "progress_billing.overrides.sales_order.validate_billing_method_lock",
	},
	"Sales Invoice": {
		"validate": "progress_billing.overrides.sales_invoice.validate_is_progress_invoice",
		"on_submit": "progress_billing.overrides.sales_invoice.update_progress_billing_status",
		"on_cancel": [
			"progress_billing.overrides.sales_invoice.update_progress_billing_status",
			"progress_billing.overrides.sales_invoice.sync_progress_billing_log_row",
		],
		"on_update": "progress_billing.overrides.sales_invoice.sync_progress_billing_log_row",
	},
}
