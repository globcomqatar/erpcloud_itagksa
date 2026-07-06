# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG and contributors
# For license information, please see license.txt

from frappe.utils import add_to_date, getdate


def validate(doc, method=None):
	set_next_reevaluation_date(doc)


def set_next_reevaluation_date(doc):
	"""Compute Next Re-Evaluation Date = base + frequency years.

	Base is the last re-evaluation date, falling back to the initial approval
	date when the supplier has never been re-evaluated. Frequency is the Select
	label ("1 Year", "2 years", ...) — the leading integer is the year count.
	"""
	base = doc.custom_last_reevaluation_date or doc.custom_initial_approval_date
	if not base or not doc.custom_frequency_of_reevaluation:
		return

	years = int(doc.custom_frequency_of_reevaluation.split()[0])
	doc.custom_next_reevaluation_date = add_to_date(getdate(base), years=years)
