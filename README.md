### ERPCloud ITAG KSA

ERPCloud Custom Development for ITAG KSA

### Changelog

### 15.13.4 — 2026-08-02

Quality Inspection in Stock Entry Connections

The Connections tab on a Stock Entry now counts and links the Quality Inspections raised from that receipt, in the same Quality group as Calibration Schedule.
Clicking through opens the inspection list filtered to that Stock Entry.
Quality Inspection points at its voucher with the reference_type / reference_name pair, so the link needs dynamic_links — without it the count would match on reference_name alone and pick up inspections belonging to other doctypes.
Purchase Receipt connections are unchanged.
No hooks.py change: override_doctype_dashboards already routed Stock Entry here.

Inward serial no longer errors as "does not exist"

Saving an inward Quality Inspection failed with "Serial No does not exist": inspection happens on the draft receipt, before the Serial No records are created, and item_serial_no is a Link to Serial No.
The serial is now stored in custom_inward_serial_no, a Select, which has nothing to resolve. Both serial fields are read-only on a Stock Entry inspection — the serial is fixed when the inspection is raised.
Inspections created before this change are still recognised, so pressing Create Quality Inspection again will not duplicate them.
custom_inward_serial_no belongs to quality_itagksa and is deliberately not in this app's fixtures — a fixture upserts by name and would reassign the field's module, leaving whichever app migrated last as its owner. after_migrate creates the field only when no app has already, so sites without quality_itagksa still get it.
Deploy: bench migrate then bench build — the fix touches a client script.


### 15.13.3 — 2026-07-29

Calibration frequency
•	Calibration Schedule has a Frequency select (Daily / Weekly / Monthly / Yearly) after End of Life Date.
•	No of Calibrations is computed from it and read-only; the generated visits are spaced by the same interval.
•	The last visit is the last one that fits on or before end of life, so it no longer always lands exactly on that date.
•	Existing submitted schedules have no Frequency; they still save, and generate_schedule asks for one.

Calibration due reminder
•	A daily task emails a "Calibration Visit Due" Notification per schedule for visits due after the lead time.
•	Lead time: ITAG KSA Settings > Calibration Reminder Days (default 7). Subject, message and recipients stay editable on the Notification itself.
•	Deploy: bench migrate — a patch seeds the Notification if it is missing.

Inward inspection
•	Create Quality Inspection appears only while serials remain uninspected, and only for ITAG KSA Settings > Inward Inspection Role. Empty role = open to everyone, as before.
•	Submitting an inward inspection returns to its Stock Entry.
•	On a receipt raised from a Sales Order, Quality Verification Required and Inward Subcontract are read-only — the mapper sets both and they gate later steps.
Not yet run against a site: no migrate, no manual test. Python, JS and DocType JSON checked only.

### 15.13.2 — 2026-07-26

Calibration plan on the schedule
Plan is set on the Calibration Schedule, not the Item: Purchase Date, End of Life Date, No of Calibrations replace Periodicity / Start / End / No of Visits.
Calibrations spread evenly between the two dates, last one on the end of life date; a date on a holiday moves back a day.
Visits are written only by the Generate Calibration Schedule button — saving the form no longer rewrites the plan. The button needs a saved schedule and disappears after submit.
Item keeps only Is Calibration Item; the Item Request Form drops to one calibration checkbox.
Calibration Schedule Item child table deleted — one schedule is one item/serial.
Deploy: patch drop_item_calibration_config_fields removes the two dead Item fields and the deleted child doctype. Guarded, so it is a no-op on a clean or fresh site.

Quality Inspections from a receipt
Stock Entry with Quality Verification Required ticked gets a Create Quality Inspection button.
Raises one draft Incoming Quality Inspection per serial, across every incoming row, then links to the list filtered to that Stock Entry.
Serials already inspected on that receipt are skipped, so pressing it again is safe.
Works on a draft receipt — inspection happens before stock is accepted. An inspection raised on a draft can only be submitted once the receipt is, since the serial does not exist as a record until then.
Readings come from the Item's Quality Inspection Template.

### 15.13.1 — 2026-07-21
- Fix a first-deploy install failure in Progress Billing: the migration that backfills existing progress invoices could crash with a database error on a brand-new site.

### 15.13.0 — 2026-07-21
- Add Progress Billing: bill Sales Orders by percentage of contract value instead of item quantity, for industries like EPC, construction, and engineering projects. Set Billing Method to Progress Billing on a submitted order, then use Create > Create Progress Invoice to raise each percentage claim. Includes a running Billing Summary and Progress Billing Log on the order, a printable Progress Billing Summary and Progress Invoice format, and a cross-order Progress Billing Summary report.

### 15.12.0 — 2026-07-15
- Calibration schedules raised from a receipt now show the item tag automatically once the receipt records it.
- A calibration schedule now carries its item, serial and tag on the schedule itself and lists them in the schedule list; the calibration lines are driven from there.
- New report of calibration visits due this month, with a one-click bulk raise of their Material Requests (one per schedule, or combined). **Report Name: Calibration Due This Month**
- Item Request Form: flag an item as a calibration item and set how often and how many times it needs calibrating; these carry over to the item that gets created.
- Item Request Form: the Has Tag and Is Calibration Item flags are shown only to Quality staff, who can now raise and approve requests.

### 15.11.1 — 2026-07-13
- Issuing serialized items to a supplier now fills the item tag automatically from the serial numbers on save, for every stock entry — not only when serials are typed in by hand.

### 15.11.0 — 2026-07-13
- Item Request Form: flag an item as customer-provided and pick the customer, and mark whether it carries a tag; these carry over to the item that gets created.
- Material Request: mark a request as a cash purchase and choose its cash supplier; a purchase order raised from it is set to that supplier automatically.
- Purchase Receipt: record the actual cash vendor's name, shown only when the supplier is the cash supplier.
- Supplier Store now prefills the moment a calibration request/order is opened, not only after the first save.
- Creating a Material Request from a Calibration Schedule now asks which specific visits it covers, instead of dumping every item.
- Calibration visits are tracked end to end: a visit is marked completed and stamped with the return date once the equipment comes back from the supplier, and the schedule shows a running "done / total" progress tally.

### 15.10.0 — 2026-07-09
- Move calibration onto a dedicated Calibration Schedule document instead of the standard Maintenance Schedule: pick an item and its serial, set frequency and number of calibrations, and generate the calibration dates. It carries an Employee rather than a Sales Person, and drops the customer and contact details.
- Flag an item as a calibration item and set how often and how many times its serials must be calibrated; when such a serial is received or created, its Calibration Schedule is raised automatically.
- A Calibration Schedule raised from a stock receipt now links back to the Stock Entry or Purchase Receipt it came from, and shows up in that document's Connections tab.
- After a calibration schedule is submitted you can still adjust its visits — reschedule a date or mark one Skipped — without cancelling the document.
- Add a Create → Material Request button on a submitted calibration schedule: it opens a new calibration-service Material Request pre-filled with each calibration item and serial, ready for the operator to add the main stock item, quantity and warehouse.

### 15.9.0 — 2026-07-09
- Move calibration onto the standard Maintenance Schedule: pick an item and its serial, set frequency and number of visits, and generate the schedule there.
- Auto-fill the serial's Item Tag on each Maintenance Schedule line and restrict the serial to the chosen item.
- Retire the previous approach — no more calibration schedule on the Serial No form, no auto-generation on receipt, no daily calibration Task, and the calibration report is removed.

### 15.8.0 — 2026-07-08
- Add tag-based calibration scheduling: mark an item as a calibration item and set how often and how many times each serial must be calibrated.
- When a serial number is created for such an item — by hand or from a stock receipt — its calibration schedule is generated automatically for every cycle.
- The Serial No screen now shows its calibration schedule directly on the form.
- On calibration Material Requests, the Calibration Item description now fills as soon as a serial is picked (not only on save) and is read-only.
- Each day, once a scheduled calibration falls due, a Task is raised automatically — titled "Calibration for <item>" with the due date as its start date.
- Add a "Calibration Schedule Per Serial No" report listing every serial's calibration cycles, due dates and status.

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
