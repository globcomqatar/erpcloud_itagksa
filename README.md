### ERPCloud ITAG KSA

ERPCloud Custom Development for ITAG KSA

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app erpcloud_itagksa
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/erpcloud_itagksa
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### Changelog

### 0.1.1 — 2026-06-30
- Add missing `Stock Entry.custom_inward_inspection_required` custom field to fixtures. The SO→Material Receipt mapping in `sales_order.py` sets this field, but the migration dropped its definition — on a fresh site the write had no backing field. Found by rehearsing the globcom decommission against a production-clone DB.

### 0.1.0 — 2026-06-30
- Migrate all `globcom_manufacturing` development into this app, reorganized into two modules: ITAG Manufacturing + ITAG Quality.
- ITAG Manufacturing: serial/heat traceability, CPI GRN rollup, Work Order FIFO serial allocation, Job Card serial gate, Production Settings (Single).
- ITAG Quality: acceptance-criteria propagation (Routing→BOM→WO→Job Card), Quality Inspection gating + auto-submit, Material Request quality flag.
- Add cross-module seam `itag_quality.job_card_inspection.validate_inspection_before_submit`, called from the Job Card `on_submit` handler.
- Wire business logic via `doc_events`; ship 58 custom fields + property setters as fixtures filtered by module; register client scripts via `doctype_js`.

### License

mit
