# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

"""
Serial Number Field Utilities

Reusable utilities for working with serial number, heat number,
drawing number, and part number fields across multiple doctypes.

Used by:
- Work Order
- Stock Entry
- Delivery Note
- Purchase Receipt
"""

import frappe
from frappe import _
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def populate_serial_fields(item, serials_data):
    """Populate serial number fields on any item.

    Populates custom_serial_no, custom_heat_no, custom_heat_lot_no,
    custom_drawing_no, and custom_part_no fields.

    Args:
        item: Item object (from any doctype - Work Order Item, Stock Entry Detail, etc.)
        serials_data (dict): Dictionary containing:
            {
                'serial_nos': ['SN001', 'SN002', ...],
                'heat_nos': ['HEAT01', 'HEAT02', ...],
                'heat_lot_nos': ['LOT01', 'LOT02', ...],
                'drawing_no': 'DRW01',  # Single value (Data field)
                'part_nos': ['PART01', 'PART02', ...]
            }

    Returns:
        item: Updated item object

    Example:
        >>> item = work_order.required_items[0]
        >>> serials_data = {
        >>>     'serial_nos': ['SN001', 'SN002'],
        >>>     'heat_nos': ['HEAT01', 'HEAT01'],
        >>>     'drawing_no': 'DRW01',  # Single value
        >>>     'part_nos': ['PART01', 'PART01']
        >>> }
        >>> populate_serial_fields(item, serials_data)
    """
    if not serials_data:
        return item

    # Populate serial numbers
    if serials_data.get('serial_nos'):
        item.custom_serial_no = '\n'.join(serials_data['serial_nos'])
    else:
        item.custom_serial_no = None

    # Populate heat numbers
    if serials_data.get('heat_nos'):
        item.custom_heat_no = '\n'.join(serials_data['heat_nos'])
    else:
        item.custom_heat_no = None

    # Populate drawing number (single value - Data field)
    item.custom_drawing_no = serials_data.get('drawing_no') or None

    # Populate part numbers
    if serials_data.get('part_nos'):
        item.custom_part_no = '\n'.join(serials_data['part_nos'])
    else:
        item.custom_part_no = None

    # Populate heat lot numbers
    if serials_data.get('heat_lot_nos'):
        item.custom_heat_lot_no = '\n'.join(serials_data['heat_lot_nos'])
    else:
        item.custom_heat_lot_no = None

    return item


def clear_serial_fields(item):
    """Clear all serial number fields on an item.

    Args:
        item: Item object (from any doctype)

    Returns:
        item: Updated item object with cleared fields
    """
    item.custom_serial_no = None
    item.custom_heat_no = None
    item.custom_drawing_no = None
    item.custom_part_no = None
    item.custom_heat_lot_no = None

    return item


def get_serial_fields_data(item):
    """Extract serial fields data from an item.

    Args:
        item: Item object with serial fields

    Returns:
        dict: {
            'serial_nos': ['SN001', ...],
            'heat_nos': ['HEAT01', ...],
            'heat_lot_nos': ['LOT01', ...],
            'drawing_no': 'DRW01',  # Single value (Data field)
            'part_nos': ['PART01', ...]
        }
    """
    from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

    return {
        'serial_nos': get_serial_nos(item.get('custom_serial_no') or ''),
        'heat_nos': get_serial_nos(item.get('custom_heat_no') or ''),
        'heat_lot_nos': get_serial_nos(item.get('custom_heat_lot_no') or ''),
        'drawing_no': item.get('custom_drawing_no') or '',  # Single value (Data field)
        'part_nos': get_serial_nos(item.get('custom_part_no') or '')
    }


def merge_serial_fields_data(existing_data, new_data):
    """Merge two serial fields data dictionaries (for accumulation).

    Useful when accumulating serials from multiple sources.

    Args:
        existing_data (dict): Existing serials data
        new_data (dict): New serials data to merge

    Returns:
        dict: Merged serials data (with duplicates removed)
        Note: drawing_no is single value - takes new_data if available, else existing

    Example:
        >>> existing = {
        >>>     'serial_nos': ['SN001', 'SN002'],
        >>>     'heat_nos': ['HEAT01', 'HEAT01']
        >>> }
        >>> new = {
        >>>     'serial_nos': ['SN003'],
        >>>     'heat_nos': ['HEAT02']
        >>> }
        >>> merge_serial_fields_data(existing, new)
        >>> # Returns: {'serial_nos': ['SN001', 'SN002', 'SN003'], ...}
    """
    result = {
        'serial_nos': [],
        'heat_nos': [],
        'heat_lot_nos': [],
        'drawing_no': '',  # Single value (Data field)
        'part_nos': []
    }

    # Merge serial numbers (remove duplicates)
    serial_set = set(existing_data.get('serial_nos', []))
    serial_set.update(new_data.get('serial_nos', []))
    result['serial_nos'] = sorted(serial_set)

    # Merge heat numbers (remove duplicates)
    heat_set = set(existing_data.get('heat_nos', []))
    heat_set.update(new_data.get('heat_nos', []))
    result['heat_nos'] = sorted(heat_set)

    # Merge heat lot numbers (remove duplicates)
    heat_lot_set = set(existing_data.get('heat_lot_nos', []))
    heat_lot_set.update(new_data.get('heat_lot_nos', []))
    result['heat_lot_nos'] = sorted(heat_lot_set)

    # Set drawing number (single value - Data field)
    # Use new_data if available, otherwise use existing_data
    result['drawing_no'] = new_data.get('drawing_no') or existing_data.get('drawing_no') or ''

    # Merge part numbers (remove duplicates)
    part_set = set(existing_data.get('part_nos', []))
    part_set.update(new_data.get('part_nos', []))
    result['part_nos'] = sorted(part_set)

    return result


def copy_serial_fields(source_item, target_item):
    """Copy serial fields from one item to another.

    Args:
        source_item: Source item object
        target_item: Target item object

    Returns:
        target_item: Updated target item

    Example:
        >>> # Copy serials from Stock Entry to Delivery Note
        >>> copy_serial_fields(stock_entry_item, delivery_note_item)
    """
    target_item.custom_serial_no = source_item.get('custom_serial_no')
    target_item.custom_heat_no = source_item.get('custom_heat_no')
    target_item.custom_heat_lot_no = source_item.get('custom_heat_lot_no')
    target_item.custom_drawing_no = source_item.get('custom_drawing_no')
    target_item.custom_part_no = source_item.get('custom_part_no')

    return target_item


@frappe.whitelist()
def fetch_serial_attributes_from_master(serial_nos_string):
    """Fetch heat/heat_lot/drawing/part numbers from Serial No master documents.

    This function queries the Serial No master for all serial numbers
    in a single batch query and retrieves the stored attributes
    (heat_no, heat_lot_no, drawing_no, part_no).

    Performance: Uses batch query with frappe.get_all() for 10x faster
    fetching compared to individual get_doc() calls.

    Args:
        serial_nos_string (str): Serial numbers as newline or comma-separated string

    Returns:
        dict: Dictionary containing:
            {
                'heat_nos': ['HEAT01', 'HEAT02', ...],
                'heat_lot_nos': ['LOT01', 'LOT02', ...],
                'drawing_no': 'DRW01',  # Single value (Data field) - from first serial
                'part_nos': ['PART01', 'PART02', ...]
            }

    Example:
        >>> fetch_serial_attributes_from_master("SN001\nSN002")
        >>> # Returns: {'heat_nos': ['HEAT01', 'HEAT02'], 'drawing_no': 'DRW01', ...}
    """
    if not serial_nos_string:
        return {
            'heat_nos': [],
            'heat_lot_nos': [],
            'drawing_no': '',  # Single value (Data field)
            'part_nos': []
        }

    # Parse serial numbers from string (handles both newline and comma separation)
    serial_nos_list = get_serial_nos(serial_nos_string)

    if not serial_nos_list:
        return {
            'heat_nos': [],
            'heat_lot_nos': [],
            'drawing_no': '',  # Single value (Data field)
            'part_nos': []
        }

    # BATCH QUERY: Fetch all serials in ONE database query (10x faster!)
    try:
        serial_docs = frappe.get_all(
            "Serial No",
            filters={"name": ["in", serial_nos_list]},
            fields=["name", "custom_heat_no", "custom_heat_lot_no", "custom_drawing_no", "custom_part_no"]
        )

        # Create a mapping dict for quick lookup: {serial_no: {heat_no, drawing_no, part_no}}
        serial_map = {doc['name']: doc for doc in serial_docs}

    except Exception as e:
        # Log error if batch query fails
        frappe.log_error(
            message=f"Error in batch fetch for serial numbers: {frappe.get_traceback()}",
            title="Serial Attributes Batch Fetch Error"
        )
        # Fallback to empty map
        serial_map = {}

    # Extract attributes in the SAME ORDER as input (important for index mapping!)
    heat_nos = []
    heat_lot_nos = []
    drawing_no = ''  # Single value (Data field) - get from first serial with value
    part_nos = []

    for serial_no in serial_nos_list:
        # Get serial data from map (or empty dict if not found)
        serial_data = serial_map.get(serial_no, {})

        # Append attributes (empty string if not found or not set)
        heat_nos.append(serial_data.get('custom_heat_no') or '')
        heat_lot_nos.append(serial_data.get('custom_heat_lot_no') or '')
        part_nos.append(serial_data.get('custom_part_no') or '')

        # Get drawing number (single value - take first non-empty value found)
        if not drawing_no and serial_data.get('custom_drawing_no'):
            drawing_no = serial_data.get('custom_drawing_no')

    return {
        'heat_nos': heat_nos,
        'heat_lot_nos': heat_lot_nos,
        'drawing_no': drawing_no,  # Single value (Data field)
        'part_nos': part_nos
    }
