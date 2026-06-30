# Production runbook — install erpcloud_itagksa, decommission globcom_manufacturing

Scope: a PROD site that already has `globcom_manufacturing` installed. Goal: erpcloud_itagksa
becomes sole owner of the manufacturing/quality custom fields + Production Settings; globcom
uninstalled. **Validated end-to-end on a restore of the `stream` prod DB (2026-06-30).**

## Corrected threat model (proven on the clone)
Frappe's `uninstall-app` deletes the Custom Field / Property Setter / DocType *definitions*
owned by the app's module. It does **NOT** physically `DROP COLUMN` — orphaned column DATA
survives (verified: 6 + 10 rows of the two dropped fields still queryable post-uninstall).
So the real risk is **loss of field DEFINITION = the field vanishes from forms/reports and any
app logic reading it breaks**, while raw bytes linger as invisible orphan columns.
Mitigation = re-own (re-tag) every still-needed field to erpcloud BEFORE uninstall so its
definition survives. Re-tag = fixture upsert rewriting `module`. No document data is moved;
same fieldname = same column.

## Pre-steps discovered by the rehearsal (a naive run crashes without these)

### P1 — fixture completeness (CODE, done in erpcloud v0.1.1)
The live prod globcom set (48 CF) ≠ erpcloud's fixture set. Diff of REAL prod vs fixtures:
- `Stock Entry.custom_inward_inspection_required` — set by erpcloud `sales_order.py:35` but the
  migration dropped its definition. **Re-added to fixtures (v0.1.1).** Preserves 25 prod rows.
- `Stock Entry.custom_drawing_no` (parent) — no erpcloud consumer (code uses the child
  `Stock Entry Detail.custom_drawing_no`). Deprecated. 6 rows. → export + let drop.
- `Quality Inspection.custom_inward_serial_no` — dead in both apps' source. 10 rows. → export + drop.
ALWAYS re-run this diff against the TARGET prod (versions drift between sites).

### P2 — stale Custom Field doc-name reconciliation (PER-SITE, run on prod before install)
Fixture import matches existing fields by Custom Field **doc name**. If a field was ever
fieldname-renamed on prod, its doc name is frozen at the old value and won't match erpcloud's
fixture name → importer INSERTs → "field already exists" → migrate aborts.
On `stream`: 1 field — live `Job Card-custom_serial_no_not_avaliable` (typo) vs fixture
`...available`. Reconcile by renaming the doc (column is keyed by fieldname, unchanged → 0 data impact):
```python
# detect
live={(r.dt,r.fieldname):r.name for r in frappe.get_all("Custom Field",
      {"module":"Globcom Manufacturing Custom"},["dt","fieldname","name"])}
# for each (dt,fieldname) also in erpcloud fixtures where live name != f"{dt}-{fieldname}":
frappe.rename_doc("Custom Field", old_name, f"{dt}-{fieldname}", force=True); frappe.db.commit()
```

### P3 — export dead-field data (ARCHIVE)
Export the 2 deprecated columns to CSV before uninstall (belt-and-suspenders; data actually
survives as orphan columns but archive it for retrievability). Saved to migration_archive/.

## Stage 0 — staging rehearsal (NON-NEGOTIABLE) — DONE for stream, PASS
Restore prod backup to a clone, run Stage 1 steps, confirm both gates + data survival.

## Stage 1 — production maintenance window
1. `bench --site <site> backup --with-files`
2. `set-maintenance-mode on`; STOP workers/scheduler. (Rehearsal proved a running worker
   injected a stray Stock Entry mid-window — maintenance mode prevents concurrent writes.)
3. Run **P2** reconciliation on prod.
4. Deploy erpcloud_itagksa @ v0.1.1. `install-app erpcloud_itagksa` (if not installed), then `migrate`.
5. **Gate A** (bench console) — all must hold:
   - `count Custom Field {module:"Globcom Manufacturing Custom"}` == only the intentionally-dropped
     dead fields (stream: 2). Every still-needed field == 0 globcom-owned.
   - `count Property Setter {module:"Globcom Manufacturing Custom"}` == 0
   - `get_value DocType "Production Settings" module` == "ITAG Manufacturing"
   If a needed field is still globcom-owned → P1/P2 incomplete; fix before continuing.
6. **Gate B** (go/no-go): `uninstall-app globcom_manufacturing --dry-run` lists ONLY the empty
   Module Def + the intentionally-dropped dead fields. Any other CF/PS/Production Settings → STOP.
   (`--dry-run` is truly read-only — verified.)
7. `uninstall-app globcom_manufacturing` (auto-backs-up first).
8. `migrate`; build assets; clear cache. `set-maintenance-mode off`; restart workers.
9. Post-checks: `list-apps` shows erpcloud not globcom; spot-check heat/serial/GRN data; functional smoke.

## Rollback
Any gate fail / bad post-check → restore Stage-1 backup. Never leave a partial uninstall.

## Rehearsal evidence (stream clone, 2026-06-30)
Gate A: CF_globcom 48→2, PS 1→0, DT(Production Settings)→ITAG Manufacturing, CF_itag=59.
Gate B dry-run: only Module Def + the 2 dead CF. Real uninstall: 0 residue, ModuleDef gone.
Data intact: Serial No heat=116, Job Card serial-gate=53, Stock Entry inward_insp=25 (kept);
the 2 dead fields' columns survived as orphans (exported regardless).

## Also
Add `required_apps = ["erpnext"]` to hooks.py before fresh-site install (prod has erpnext; low risk).
