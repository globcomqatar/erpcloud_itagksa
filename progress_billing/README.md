# Progress Billing

Adds percentage-of-contract-value invoicing to ERPNext Sales Orders, for
industries that bill by contract completion percentage (EPC, industrial
manufacturing, construction, engineering projects) rather than item
quantity.

## Install

    bench get-app progress_billing /path/to/apps/progress_billing
    bench --site your-site.local install-app progress_billing

## Usage

1. On a Sales Order, set **Billing Method** to **Progress Billing** before
   or after submit.
2. Submit the Sales Order.
3. Use **Create > Create Progress Invoice**, enter a billing percentage,
   and a draft Sales Invoice is generated with every line's rate scaled to
   that percentage (quantity is left unchanged).
4. Repeat until 100% is billed — **Progress Billing Status** on the Sales
   Order then flips to **Completed**.
5. See the **Progress Billing Summary** report for a cross-order view of
   contract value, percentage billed, and remaining amount.

## Progress Billing Log

Every progress invoice automatically creates a row in the **Progress Billing Log**
table on its Sales Order — Progress No., Billing Date, Billing %, Invoice Amount,
linked Sales Invoice, Invoice Status (Draft/Submitted/Cancelled), Amount Paid,
Outstanding Amount, and Payment %. Progress No. is assigned once and never
renumbered, even if a later invoice is cancelled.

Amount Paid / Outstanding / Payment % are refreshed live from each invoice's own
balance every time the Sales Order is opened — since ERPNext updates an invoice's
balance via a direct database write when a payment posts (not through a document
save), there's no reliable event to push those numbers to us; reading them fresh
on every view avoids ever showing stale figures. The Print Format computes its own
live paid/outstanding figures the same way, since printing does not trigger this
refresh.

The **Billing Summary** section above the log (Contract Value, Total Progress
Invoiced, Total Amount Received, Outstanding Amount, Remaining %) is computed
from the log's own rows, excluding any cancelled invoices. Its Total Progress
Invoiced/Remaining % always reflect the Sales Order's own authoritative billed
percentage even if some historical invoices aren't in the log yet; the invoiced/
received amounts reflect only what has been logged.

Use **Print > Progress Billing Summary** on a Progress Billing Sales Order for a
customer-shareable printout of the same history.

Existing progress invoices from before this feature shipped were backfilled by
a one-time migration patch — no action needed.

## Scope

Out of scope for v1: named milestone billing schedules, per-item
percentage overrides, retention/holdback handling. See
`docs/superpowers/specs/2026-07-16-progress-billing-design.md` in the
planning repo for the full design rationale.
