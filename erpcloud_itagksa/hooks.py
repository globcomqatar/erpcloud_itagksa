app_name = "erpcloud_itagksa"
app_title = "ERPCloud ITAG KSA"
app_publisher = "Globcom Qatar"
app_description = "ERPCloud Custom Development for ITAG KSA"
app_email = "info@globcomqatar.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "erpcloud_itagksa",
# 		"logo": "/assets/erpcloud_itagksa/logo.png",
# 		"title": "ERPCloud ITAG KSA",
# 		"route": "/erpcloud_itagksa",
# 		"has_permission": "erpcloud_itagksa.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpcloud_itagksa/css/erpcloud_itagksa.css"
# app_include_js = "/assets/erpcloud_itagksa/js/erpcloud_itagksa.js"

# include js, css files in header of web template
# web_include_css = "/assets/erpcloud_itagksa/css/erpcloud_itagksa.css"
# web_include_js = "/assets/erpcloud_itagksa/js/erpcloud_itagksa.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "erpcloud_itagksa/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "erpcloud_itagksa/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "erpcloud_itagksa.utils.jinja_methods",
# 	"filters": "erpcloud_itagksa.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "erpcloud_itagksa.install.before_install"
# after_install = "erpcloud_itagksa.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "erpcloud_itagksa.uninstall.before_uninstall"
# after_uninstall = "erpcloud_itagksa.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "erpcloud_itagksa.utils.before_app_install"
# after_app_install = "erpcloud_itagksa.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "erpcloud_itagksa.utils.before_app_uninstall"
# after_app_uninstall = "erpcloud_itagksa.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpcloud_itagksa.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"erpcloud_itagksa.tasks.all"
# 	],
# 	"daily": [
# 		"erpcloud_itagksa.tasks.daily"
# 	],
# 	"hourly": [
# 		"erpcloud_itagksa.tasks.hourly"
# 	],
# 	"weekly": [
# 		"erpcloud_itagksa.tasks.weekly"
# 	],
# 	"monthly": [
# 		"erpcloud_itagksa.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "erpcloud_itagksa.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "erpcloud_itagksa.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "erpcloud_itagksa.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["erpcloud_itagksa.utils.before_request"]
# after_request = ["erpcloud_itagksa.utils.after_request"]

# Job Events
# ----------
# before_job = ["erpcloud_itagksa.utils.before_job"]
# after_job = ["erpcloud_itagksa.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"erpcloud_itagksa.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# ITAG customization
# ==================
# Migrated from globcom_manufacturing. Two modules: ITAG Manufacturing + ITAG Quality.

doc_events = {
	"Stock Entry": {
		"before_validate": "erpcloud_itagksa.itag_manufacturing.stock_entry.stock_entry.before_validate",
		"validate": "erpcloud_itagksa.itag_manufacturing.stock_entry.stock_entry.validate",
		"on_submit": "erpcloud_itagksa.itag_manufacturing.stock_entry.stock_entry.on_submit",
		"on_cancel": "erpcloud_itagksa.itag_manufacturing.stock_entry.stock_entry.on_cancel",
	},
	"BOM": {
		"before_save": "erpcloud_itagksa.itag_quality.acceptance_criteria.acceptance_criteria.propagate_bom_from_routing",
	},
	"Work Order": {
		"validate": [
			"erpcloud_itagksa.itag_manufacturing.work_order.work_order.validate",
			"erpcloud_itagksa.itag_quality.acceptance_criteria.acceptance_criteria.propagate_wo_from_bom",
		],
		"after_insert": "erpcloud_itagksa.itag_manufacturing.work_order.work_order.after_insert",
	},
	"Job Card": {
		"validate": "erpcloud_itagksa.itag_manufacturing.job_card.job_card.validate",
		"before_save": "erpcloud_itagksa.itag_manufacturing.job_card.job_card.before_save",
		"on_submit": "erpcloud_itagksa.itag_manufacturing.job_card.job_card.on_submit",
		"on_update": "erpcloud_itagksa.itag_manufacturing.job_card.job_card.on_update",
		"on_cancel": "erpcloud_itagksa.itag_manufacturing.job_card.job_card.on_cancel",
	},
	"Quality Inspection": {
		"on_submit": "erpcloud_itagksa.itag_quality.quality_inspection.quality_inspection.on_submit",
	},
	"Material Request": {
		"before_save": "erpcloud_itagksa.itag_quality.material_request.material_request.before_save",
	},
}

doctype_js = {
	"Sales Order": "itag_manufacturing/sales_order/sales_order.js",
	"Stock Entry": "itag_manufacturing/stock_entry/stock_entry.js",
	"Job Card": "itag_manufacturing/job_card/job_card.js",
	"Work Order": "itag_manufacturing/work_order/work_order.js",
}

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["module", "in", ["ITAG Manufacturing", "ITAG Quality"]]],
	},
	{
		"dt": "Property Setter",
		"filters": [["module", "in", ["ITAG Manufacturing", "ITAG Quality"]]],
	},
	{
		"dt": "Stock Entry Type",
		"filters": [["name", "in", ["Material Receipt - CPI", "Material Return - CPI"]]],
	},
]

