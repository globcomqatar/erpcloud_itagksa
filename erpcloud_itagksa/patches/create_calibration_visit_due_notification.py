# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG and contributors
# For license information, please see license.txt

"""Seed the Notification fired by the daily calibration reminder.

The reminder is raised in code (itag_quality/tasks.py) because a Notification
cannot target a visit row, but its wording and recipients belong to the admin.
Seeding the record create-if-missing gives them an editable starting point that
a later migrate will not overwrite.
"""

import frappe

NOTIFICATION_NAME = "Calibration Visit Due"
RECIPIENT_ROLE = "Quality Manager"

SUBJECT = "Calibration due: {{ doc.item_code }} ({{ doc.serial_no }})"

MESSAGE = """<p>The calibration visits below are due on <b>{{ doc.name }}</b>.</p>

<table border="1" cellpadding="6" cellspacing="0">
	<tr>
		<th>Item</th>
		<th>Serial No</th>
		<th>Scheduled Date</th>
		<th>Employee</th>
	</tr>
	{% for visit in doc.due_visits %}
	<tr>
		<td>{{ visit.item_name or visit.item_code }}</td>
		<td>{{ visit.serial_no or "" }}</td>
		<td>{{ frappe.utils.formatdate(visit.scheduled_date) }}</td>
		<td>{{ visit.employee_name or "" }}</td>
	</tr>
	{% endfor %}
</table>
"""


def execute():
	if frappe.db.exists("Notification", NOTIFICATION_NAME):
		return

	notification = frappe.get_doc(
		{
			"doctype": "Notification",
			"name": NOTIFICATION_NAME,
			"subject": SUBJECT,
			"document_type": "Calibration Schedule",
			"event": "Method",
			"method": "calibration_visit_due",
			"channel": "Email",
			"send_system_notification": 1,
			"enabled": 1,
			"is_standard": 0,
			"message": MESSAGE,
		}
	)

	# A site without the ERPNext quality roles would fail the link validation on
	# insert. Seed it without recipients instead so the admin picks their own.
	if frappe.db.exists("Role", RECIPIENT_ROLE):
		notification.append("recipients", {"receiver_by_role": RECIPIENT_ROLE})

	notification.insert(ignore_permissions=True)
	frappe.db.commit()
