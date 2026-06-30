# Migration verification checklist — globcom_manufacturing → erpcloud_itagksa

Plain-language list for manual verification. Check each in Desk after deploy.
59 custom fields total + the development (code) below.

## Custom fields — ITAG Manufacturing module

Verify in **Customize Form** or **Custom Field list** (filter module = "ITAG Manufacturing").

- **Item** — Product Type
- **Job Card** (10) — Customer Name, Drawing No, Heat Lot No, Heat No, Item Description, Operation Description, Part No, Sales Order, Serial No Not Available, Work Order Serial No
- **Job Card Time Log** (6) — Column Break, Drawing No, Heat No, Part Nos, Serial Details, Serial No
- **Purchase Order Item** — Product Type
- **Purchase Receipt Item** — Product Type
- **Sales Order** (3) — Drawing No, GRN Status, Subcontracted Job
- **Serial No** (4) — Drawing No, Heat Lot No, Heat No, Part No
- **Stock Entry** (9) — Customer, Customer Name (CPI), Customer PO No, Customer Property GRN, Customer Property Return, Customer Sales Order Number, Delivery Note (CPI), Inward Inspection Required, Subcontracted Job
- **Stock Entry Detail** (4) — Drawing No, Heat Lot No, Heat No, Part No
- **Work Order** (6) — Customer Name, Drawing No, Job Cards Completed, Serial No, Stock Entry, Subcontracted Job
- **Work Order Item** (7) — Column Break, Drawing No, Heat Lot No, Heat No, Part No, Serial No, Serial No And Other Details

## Custom fields — ITAG Quality module

Filter module = "ITAG Quality".

- **BOM Operation** — Acceptance Criteria
- **Job Card** (2) — Acceptance Criteria, Inspection Required
- **Material Request** — Quality Verification Required
- **Material Request Item** — Product Type
- **Work Order Operation** (2) — Acceptance Criteria, Quality Inspection Required

## Development (code) migrated

### ITAG Manufacturing
- **Stock Entry** — validate, on_submit, on_cancel (serial/heat handling, CPI receipt)
- **Work Order** — validate, after_insert (FIFO serial allocation, customer fields)
- **Job Card** — validate, before_save, on_submit, on_update, on_cancel (serial gate)
- **Sales Order** — GRN status rollup; sets Inward Inspection Required on SO→Material Receipt map
- **Production Settings** (Single DocType) — config, now owned by ITAG Manufacturing
- Client scripts: Sales Order, Stock Entry, Job Card, Work Order
- Stock Entry Types: "Material Receipt - CPI", "Material Return - CPI"

### ITAG Quality
- **Quality Inspection** — on_submit (gating + auto-submit)
- **Acceptance Criteria** — propagates Routing → BOM → Work Order → Job Card
- **Material Request** — before_save (quality flag)
- **Cross-module seam** — Job Card on_submit calls `validate_inspection_before_submit` (requires linked QI submitted + Accepted when inspection required)

## After globcom uninstall — confirm
- Custom Field list filter module = "Globcom Manufacturing Custom" → only the 2 intentionally-dropped dead fields remain (then gone after uninstall)
- Property Setter, same filter → 0
- Production Settings DocType module = ITAG Manufacturing
- Spot-check live data intact: Serial No heat/part, Job Card serials, Sales Order GRN status
