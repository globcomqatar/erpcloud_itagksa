# erpcloud_itagksa — App Instructions

Unified ITAG KSA app. Manufacturing + quality customization migrated from
`globcom_manufacturing` (2026-06-30), reorganized into two capability modules:
**ITAG Manufacturing** + **ITAG Quality** (inner pkg `erpcloud_itagksa`).

---

## RELEASE RULE — branch + PR, no version bump

Ship every change on a branch and merge it through a pull request. **No version bump,
no README changelog entry.** Do not touch `__version__` in `erpcloud_itagksa/__init__.py`
and do not add to `## Changelog` in `README.md` — the git history and the PR are the record.

Never commit straight to `main`, never push `main`.

### Flow
1. Branch off current `main`: `feat/<short-slug>` for new behavior, `fix/<short-slug>` for a bug fix.
2. Commit the work on that branch.
3. Push it: `git push -u upstream feat/<short-slug>` — `upstream` is the only remote
   (`globcomqatar/erpcloud_itagksa`); there is no `origin`.
4. Open the PR with `gh`, base `main`:
   `gh pr create --base main --head feat/<short-slug> --title "..." --body "..."`
5. Leave the merge to the reviewer. Do not self-merge unless asked.

### PR content
Title: one line, plain language, what the change does for the user.
Body: what changed and why, plus how to verify it manually. Same plain-language rule the
changelog had — describe the user-facing change, not the implementation.

**Keep it short.** Same sections, a fraction of the words. Target ~40 lines; if it runs past
one screen it is too long. The reviewer reads the diff for detail — the PR body only orients them.

- One `##` section per feature, plus one `## Verify` at the end. No sub-headings, no tables.
- Bullets, not paragraphs. One line each. No line restates another.
- Skip the rationale unless a decision looks wrong without it — then one clause, not a paragraph.
- Verify steps: numbered, one action each, only the paths a reviewer would actually click.
- No "Notes" section restating the release rule, and no closing summary.

Template:

```markdown
## <Feature>
- <what changed, user-facing>
- <what changed, user-facing>
- Deploy: <patch or migrate step, only if there is one>

## Verify
1. <action → expected result>
2. <action → expected result>
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
  `property_setter.json`), filtered by `module in ["ITAG Manufacturing", "ITAG Quality",
  "ITAG Stock", "Itag Ksa Buying"]`. Stock Entry Types ship too.
- **Never `bench export-fixtures` to add a custom field.** Export re-snapshots the whole
  DB for those modules — it pulls in any drift field the DB has but the fixture doesn't,
  and re-serializes/re-timestamps every entry, producing a huge noisy diff. Instead
  **hand-append the new field object(s)** to `custom_field.json` (set `module`,
  `is_system_generated: 1`, and a `name` of `"<DocType>-<fieldname>"`), then `bench migrate`.
- **Master records are not fixtures.** A Supplier fixture would upsert and overwrite a
  live record's real data. The `Cash Supplier` master (default on cash-purchase Material
  Requests) is seeded create-if-missing by `install.after_install → ensure_cash_supplier`.
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
