# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ItemRequestForm(Document):
	def on_submit(self):
		self._create_item()

	def _create_item(self):
		if self.created_item:
			return

		item = frappe.new_doc("Item")
		item.item_code = self.item_short_name
		item.item_name = self.item_short_name
		item.item_group = self.item_group
		item.description = self.item_description
		item.stock_uom = self.item_uom
		item.is_stock_item = self.maintain_stock
		item.has_serial_no = self.has_serial_no
		item.custom_product_type = self.item_type
		item.insert(ignore_permissions=True)

		self.db_set("created_item", item.name)
		frappe.msgprint(
			_("Item {0} created.").format(frappe.utils.get_link_to_form("Item", item.name)),
			alert=True,
		)
