import frappe

# Parent header checkbox -> value written to each child line's Item Type field.
FLAG_TO_VALUE = {
	"custom_critical": "Critical",
	"custom_noncritical": "Non-Critical",
	"custom_general": "General",
}
TARGET_FIELD = "custom_product_type"
PARENT_CHILD = {
	"Material Request": "Material Request Item",
	"Purchase Order": "Purchase Order Item",
}


def execute():
	"""Backfill the line Item Type (`custom_product_type`) from the parent header's
	Critical / Non-Critical / General checkboxes on submitted documents.

	One checkbox ticked on the header -> every line on that document gets the matching
	Item Type. Runs only for submitted parents (docstatus=1) that have exactly one
	checkbox set, so there is no ambiguity about which value to write.

	Field-availability guarded: a doctype is skipped unless the child has the target
	field and the parent carries at least one source checkbox. The KSA and Qatar stacks
	don't both have these header checkboxes, so the guard lets one patch run safely on
	either. Idempotent: re-running writes the same values.
	"""
	for parent_dt, child_dt in PARENT_CHILD.items():
		_backfill(parent_dt, child_dt)
	frappe.db.commit()


def _backfill(parent_dt, child_dt):
	if not frappe.db.has_column(child_dt, TARGET_FIELD):
		print(f"skip {parent_dt}: {child_dt}.{TARGET_FIELD} not present")
		return

	flags = [f for f in FLAG_TO_VALUE if frappe.db.has_column(parent_dt, f)]
	if not flags:
		print(f"skip {parent_dt}: no source checkboxes on header")
		return

	case_clause = " ".join(f"when parent.`{f}` = 1 then %s" for f in flags)
	sum_clause = " + ".join(f"coalesce(parent.`{f}`, 0)" for f in flags)
	values = [FLAG_TO_VALUE[f] for f in flags]

	join_and_filter = f"""
		from `tab{child_dt}` child
		join `tab{parent_dt}` parent
			on child.parent = parent.name and child.parenttype = %s
		where parent.docstatus = 1 and ({sum_clause}) = 1
	"""

	affected = frappe.db.sql(f"select count(*) {join_and_filter}", [parent_dt])[0][0]

	frappe.db.sql(
		f"""
		update `tab{child_dt}` child
		join `tab{parent_dt}` parent
			on child.parent = parent.name and child.parenttype = %s
		set child.`{TARGET_FIELD}` = case {case_clause} end
		where parent.docstatus = 1 and ({sum_clause}) = 1
		""",
		[parent_dt, *values],
	)

	print(f"backfilled {parent_dt}: {affected} {child_dt} lines")
