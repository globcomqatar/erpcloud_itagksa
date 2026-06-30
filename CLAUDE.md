# erpcloud_itagksa — App Instructions

Unified ITAG KSA app. Manufacturing + quality customization migrated from
`globcom_manufacturing` (2026-06-30), reorganized into two capability modules:
**ITAG Manufacturing** + **ITAG Quality** (inner pkg `erpcloud_itagksa`).

---

## RELEASE RULE — required before every push to GitHub

Every push to GitHub MUST first include both of these, in the same commit/PR:

1. **Version bump** in `erpcloud_itagksa/__init__.py` (`__version__`, currently `0.0.1`).
2. **Changelog entry** in `README.md` under `## Changelog` — new version, date, summary of changes.

No push without both. A code change with no version bump and no changelog entry is incomplete.

### Versioning (semver)
- **patch** (`x.y.Z`) — bug fix, no behavior change.
- **minor** (`x.Y.0`) — new feature, backward compatible.
- **major** (`X.0.0`) — breaking change (doctype/API/fixture change that needs migration).

### Changelog entry format
```
## Changelog

### 0.1.0 — 2026-06-30
- Short bullet per change. Imperative mood.
```

---

## Architecture
- Business logic lives in **module handlers** wired via `doc_events` in `hooks.py`,
  not in standalone doctype controllers (this app overrides no controller class).
- **ITAG Manufacturing** (`itag_manufacturing/`) — serial/heat traceability, CPI GRN
  rollup, Work Order FIFO serial allocation, Job Card serial gate. Handlers:
  `stock_entry/`, `work_order/`, `job_card/`, `sales_order/`, `utils/`.
- **ITAG Quality** (`itag_quality/`) — acceptance-criteria propagation
  (Routing→BOM→WO→Job Card), Quality Inspection gating + auto-submit, Material Request
  quality flag. Handlers: `quality_inspection/`, `acceptance_criteria/`, `material_request/`.
- **Custom DocType:** `Production Settings` (Single) is owned by module ITAG Manufacturing.
- Custom fields / property setters ship as **fixtures** (`fixtures/custom_field.json`,
  `property_setter.json`), filtered by `module in ["ITAG Manufacturing", "ITAG Quality"]`
  (58 fields). Stock Entry Types "Material Receipt - CPI" / "Material Return - CPI" ship too.
- Client scripts in `itag_manufacturing/<doctype>/<doctype>.js`, wired via `doctype_js`
  in `hooks.py` (Sales Order, Stock Entry, Job Card, Work Order).

## The cross-module seam
- `itag_quality/job_card_inspection.py::validate_inspection_before_submit` — extracted
  from globcom's Job Card `on_submit`. Gates Job Card submission on a linked
  Quality Inspection that is submitted (`docstatus=1`) and `status="Accepted"` when
  `custom_inspection_required`.
- Called from `itag_manufacturing/job_card/job_card.py::on_submit` — **single import
  across the seam, no duplication.** Keep it that way: quality owns the gate, manufacturing
  calls it. Do not inline the check back into the Job Card handler.

## Patches
- Follow the project root rule: never write a patch unless explicitly asked and approved.
- Idempotent only — guard with `frappe.db.exists(...)`, `ignore_permissions=True`, explicit
  `frappe.db.commit()`.
- Register in `patches.txt` (`[post_model_sync]` for data, `[pre_model_sync]` for schema prep).

## Deploy prereq
- App depends on **erpnext**: every `doc_events` target and most fixtures are erpnext
  doctypes (Stock Entry, BOM, Work Order, Job Card, Quality Inspection, Material Request,
  Sales Order). `bench migrate` / runtime hooks fail without erpnext installed.
- `required_apps` is **not yet declared** in `hooks.py` (still commented). Add
  `required_apps = ["erpnext"]` before shipping to a fresh site.

## Migration origin / parallel stacks
- Additive migration onto **itagksa.dev** only — `globcom_manufacturing` is NOT installed
  there (it lives on the Qatar/test sites). Nothing was uninstalled on KSA.
- Coexists with installed app **quality_itagksa** — 0 custom-field overlap; both hook
  Job Card events with distinct fieldnames. Do not assume one owns the other's fields.
