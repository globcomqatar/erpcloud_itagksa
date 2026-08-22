# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG KSA and contributors
# For license information, please see license.txt

"""Make sure the roles the bid approval workflow names are on the site.

Roles are not fixtures, so a site can be missing them and the workflow then
fails to insert on Only Allow Edit For and Allowed. Each role is created only
when absent, so a site that already has one keeps its users and its permissions.

CEO Approval was called CEO Review until August 2026. Where the old name is
still on the site it is renamed rather than replaced, so whoever holds the role
keeps it.
"""

import frappe

RENAMED_ROLES = [("CEO Review", "CEO Approval")]

REVIEW_ROLES = [
	"Manufacturing Review",
	"Quality Review",
	"Operation Review",
	"Finance Review",
	"CEO Approval",
]


def execute():
	for old_name, new_name in RENAMED_ROLES:
		rename_role(old_name, new_name)

	for role in REVIEW_ROLES:
		create_missing_role(role)

	frappe.db.commit()


def rename_role(old_name, new_name):
	if frappe.db.exists("Role", new_name) or not frappe.db.exists("Role", old_name):
		return

	frappe.rename_doc("Role", old_name, new_name)


def create_missing_role(role):
	if frappe.db.exists("Role", role):
		return

	frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
		ignore_permissions=True
	)
