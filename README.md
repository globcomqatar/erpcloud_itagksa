### ERPCloud ITAG KSA

ERPCloud Custom Development for ITAG KSA

### Changelog

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
