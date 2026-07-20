import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "width": 130},
		{"label": _("% Billed"), "fieldname": "percent_billed", "fieldtype": "Percent", "width": 100},
		{"label": _("Remaining %"), "fieldname": "remaining_percent", "fieldtype": "Percent", "width": 100},
		{"label": _("Remaining Amount"), "fieldname": "remaining_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Invoice Count"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 100},
		{"label": _("Last Invoice Date"), "fieldname": "last_invoice_date", "fieldtype": "Date", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	filters = filters or {}
	conditions = ["so.pb_billing_method = 'Progress Billing'", "so.docstatus = 1"]
	values = {}

	if filters.get("company"):
		conditions.append("so.company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("customer"):
		conditions.append("so.customer = %(customer)s")
		values["customer"] = filters["customer"]

	sales_orders = frappe.db.sql(
		f"""
		select
			so.name as sales_order,
			so.customer as customer,
			so.grand_total as contract_value,
			so.per_billed as percent_billed,
			so.pb_progress_billing_status as status
		from `tabSales Order` so
		where {" and ".join(conditions)}
		order by so.transaction_date desc
		""",
		values,
		as_dict=True,
	)

	data = []
	for so in sales_orders:
		invoice_stats = frappe.db.sql(
			"""
			select count(name) as invoice_count, max(posting_date) as last_invoice_date
			from `tabSales Invoice`
			where pb_against_sales_order = %s and docstatus = 1
			""",
			so.sales_order,
			as_dict=True,
		)[0]

		percent_billed = flt(so.percent_billed)
		remaining_percent = 100 - percent_billed
		contract_value = flt(so.contract_value)

		data.append(
			{
				"sales_order": so.sales_order,
				"customer": so.customer,
				"contract_value": contract_value,
				"percent_billed": percent_billed,
				"remaining_percent": remaining_percent,
				"remaining_amount": contract_value * remaining_percent / 100,
				"invoice_count": invoice_stats.invoice_count or 0,
				"last_invoice_date": invoice_stats.last_invoice_date,
				"status": so.status or "In Progress",
			}
		)

	return data
