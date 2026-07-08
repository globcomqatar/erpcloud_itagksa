### ERPCloud ITAG KSA

ERPCloud Custom Development for ITAG KSA

### Changelog

### 15.7.0 — 2026-07-08
- Item Request Form: Item Type is now required, add a "Has Tag" checkbox, and let stock, purchase, sales, manufacturing, accounts and projects staff create and submit requests.
- Add a Default Supplier Store setting that prefills the Supplier Store on new Material Requests and Purchase Orders.
- On calibration Material Requests, show the serial's Item Tag as its own column before the serial field, and make the Calibration Item Description editable.
- Rename "Calibration Item" to "Calibration Item code" on Material Requests and Purchase Orders.
- Drop the inline serial-tag text in the serial picker (it wasn't working) and name that field simply "Serial No".

### 15.6.0 — 2026-07-07
- Add an **Item Request Form**: staff raise a request for a new item (short name, item group, description, UOM, item type, maintain-stock and has-serial-no flags). A Stock Manager approves it by submitting, and the Item record is created automatically on submit. The item code is assigned by the site's item naming rule — the requester never types one. The created Item is linked back on the request for traceability.

### 15.5.1 — 2026-07-07
- On material issues and transfers, fill each row's Item Tag from its serial numbers automatically, and block saving if a typed tag does not match the serial.
- Rename the Item "Track Item Tags" checkbox to "Has Item Tag".
- On calibration Material Requests and Purchase Orders, show the serial's Item Tag inline in the serial picker and relabel that field "Serial No/Item Tag".
- Stop the calibration serial from being cleared the moment it is selected.
- Add a Supplier Store to calibration Material Requests that carries over to the Purchase Order.
- Extend the calibration Purchase Order status to "Partially Received" / "Fully Received" once goods return from the supplier; the Material Issue button no longer reopens after a return.

### 15.5.0 — 2026-07-06
- Capture one Item Tag per serial number on stock and purchase receipts when the item tracks tags — tags are entered line-by-line like heat numbers, validated one-to-one against the serials, and written onto each serial number. Item tags are searchable from the serial-number lookup.
- Show the Calibration Service flag on Material Request only to Quality staff.
- On Purchase Orders and Stock Entries, show the calibration and quality-verification flags only once they are set.
- Rename the Stock Entry calibration flags to "Calibration Item Material Issue" and "Calibration Item Material Receipt".

### 15.4.0 — 2026-07-06
- Supplier Approval: auto-fill the next re-evaluation date from the last re-evaluation (or first approval) plus the chosen frequency.
- Freeze a supplier automatically once its re-evaluation is due or any of its documents expire; unfreezing stays manual.
- Show the Supplier Approval tab only to the role set in ITAG KSA Settings.

### 15.3.2 — 2026-07-03
- Backfill the line Item Type on already-submitted Material Requests and Purchase Orders from the header Critical / Non-Critical / General checkbox — one ticked box sets that type on every line. Skips documents with no box or more than one box ticked.

### 15.3.1 — 2026-07-02
- Sales Order now lists its linked Stock Entries in the Connections panel.
- Ship the new ITAG Stock custom fields as app fixtures so they deploy with the app.

### 15.3.0 — 2026-07-02
- Add the Calibration / Collaboration Service PO flow (ported from `erpcloud_itagqatar`, f004): `custom_is_collaboration_service_po` flag on Material Request + Purchase Order enables per-row `custom_sub_item` (Calibration Item), `custom_serial_no`, read-only `custom_sub_item_description` on the item tables (first-section second column). MR flag sits at the end of the first-section right column.
- Material Issue button on a submitted collab PO maps it to an Issue Stock Entry (`Material Issue to Supplier`); Create GRN button on the Issue SE maps back to a Receipt SE (`Material Receipt from Supplier`). PO `custom_collaboration_status` rolls up Pending → Partially → Fully Issued from submitted Issue SEs.
- Serial validation on MR + PO (`utils/collab_serial.py`). `validate_receipt_qty` toggle on `ITAG KSA Settings` gates the GRN receipt-qty guard. New Stock Entry Types + `hooks.py` wiring (list-form `doc_events`, `doctype_js`, `app_include_js`).

### 15.2.0 — 2026-07-01
- Add `ITAG KSA Settings` (Single) with `default_target_warehouse` (Link → Warehouse) — the default receiving warehouse for the CPI GRN made from a Sales Order.
- Default the target warehouse on CPI GRNs via a Stock Entry `before_validate` handler (`set_default_target_warehouse`): fills `to_warehouse` and any empty item `t_warehouse` for stock entry type `Material Receipt - CPI`. Runs before ERPNext's `validate_warehouse`, so the "Target warehouse is mandatory" throw no longer blocks the save. Path-independent — covers the Sales Order GRN button, the `custom_customer_property_grn` checkbox, and manual entry. Wired via `doc_events.before_validate` in `hooks.py`.
- Pre-fill the CPI GRN target warehouse client-side (`stock_entry.js` `apply_cpi_default_warehouse`) on `refresh` / `stock_entry_type` / `items_add`, with a `show_alert` notice so the user sees it is auto-filled before saving. Display only; the `before_validate` handler stays authoritative on save. Skips if the user already chose a warehouse.
- Relabel `Stock Entry.custom_inward_inspection_required` → "Quality Verification Required", description "Only for customer property items" (fieldname unchanged — no data impact).

### 15.1.4 — 2026-06-30
- Fix install/migrate abort `A field with the name <x> already exists` when a target site has a Custom Field whose doc name no longer matches this app's fixture (e.g. a field that was fieldname-renamed in globcom, leaving a frozen/typo'd doc name). Add `reconcile_stale_custom_field_names`, run from both a `before_install` hook (fresh-install path) and a `pre_model_sync` patch (migrate/retry path), so a console-less deploy self-heals either way. Fixture-driven and idempotent; renames the live doc to the fixture name (column keyed by fieldname → 0 data impact), and the fixture sync then re-owns its module.

### 15.1.3 — 2026-06-30
- Rename `custom_product_type` Select option `Non-Product` → `General` on Item, Purchase Order Item, Purchase Receipt Item, and Material Request Item.
- Add post_model_sync patch `rename_product_type_option` that rewrites existing stored `Non-Product` values to `General` on those doctypes (idempotent, column-guarded) — the option rename alone does not update existing rows.

### 0.1.2 — 2026-06-30
- Add missing `Stock Entry.custom_inward_inspection_required` custom field to fixtures. The SO→Material Receipt mapping in `sales_order.py` sets this field, but the migration dropped its definition — on a fresh site the write had no backing field. Found by rehearsing the globcom decommission against a production-clone DB.
- Migrate all `globcom_manufacturing` development into this app, reorganized into two modules: ITAG Manufacturing + ITAG Quality.
- ITAG Manufacturing: serial/heat traceability, CPI GRN rollup, Work Order FIFO serial allocation, Job Card serial gate, Production Settings (Single).
- ITAG Quality: acceptance-criteria propagation (Routing→BOM→WO→Job Card), Quality Inspection gating + auto-submit, Material Request quality flag.
- Add cross-module seam `itag_quality.job_card_inspection.validate_inspection_before_submit`, called from the Job Card `on_submit` handler.
- Wire business logic via `doc_events`; ship 58 custom fields + property setters as fixtures filtered by module; register client scripts via `doctype_js`.

### License

mit
