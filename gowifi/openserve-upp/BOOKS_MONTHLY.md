# GoWifi monthly books

Checksum: the amount due on https://gowifi.co.za/dash/clients.html equals that customer’s open balance in QuickBooks. After 17 October 2026 those two figures match for every client on the page.

GOWIFI (PTY) LTD is not VAT registered. An invoice goes out on the 17th for the next month’s service. A debit order normally collects on the 1st of that next month. 5 October 2026 was a same-day batch. The November 2026 batch is set for 2 November.

Netcash is read-only. This run never uploads a batch and never deploys the site.

## Accounts

| Id | Account | Use |
|---|---|---|
| 78 | FNB 62860060278 Main | Client EFTs, expenses, and the lump received from Netcash |
| 79 | Netcash – Debit Orders | Client debit-order receipts, fees, interest, transfer out to FNB |
| 69 | Services | Invoice income |
| 87 | Bank charges: Netcash | Service charges |
| 88 | Netcash interest income | Interest in |
| 89 | Netcash interest expense | Interest out |

An FNB line memo `NETCASH …NETCASH` is a transfer from account 79 to account 78. It is the settlement after fees. It is not a client receipt and it is not income.

## Standing list — bill from this

`billing.py` `CLIENTS` is behind the books. Annette Bing HH is R439 here and still R429 in that file. Derek van Zyl and Whale Rock Lodge are on the books and missing from that file. Use this table until that list is updated. Do not run `billing.py` `run_cycle` as the QuickBooks invoice run: it writes a local shadow (`gowifi-do` / `gowifi-eft`) and that shadow must not be paid a second time.

Debit order, 15 clients, R9,986 at these amounts. The batch already authorised for 2 November 2026 was loaded at R9,976 because Annette Bing HH was still R429 on that sheet.

| Client | Monthly | Method |
|---|---:|---|
| Phillip De Gruchy | 1,219 | Debit order |
| Bryant Michael | 759 | Debit order |
| GeoCorp | 759 | Debit order |
| G Cupido | 759 | Debit order |
| Hermanus Builders | 759 | Debit order |
| Murray DH | 759 | Debit order |
| Gordon Neethling | 759 | Debit order |
| Derek van Zyl | 759 | Debit order |
| Havenga | 699 | Debit order |
| Bing Noordhoek Fibre | 599 | Debit order |
| Jean de Villiers | 550 | Debit order |
| David Wantling | 439 | Debit order |
| Annette Bing HH | 439 | Debit order |
| Dirk De Villiers | 399 | Debit order |
| Stan Hundermark | 329 | Debit order |
| Whale Rock Lodge | 1,759 | EFT until her own Netcash line is on a batch |
| Paltco | 1,399 | EFT (loan contribution, still a sales invoice) |
| WCC Tech | 1,000 | EFT |
| Lategan | 999 | EFT |
| HPP Control Room | 599 | EFT |
| Phillipus May | 439 | EFT |
| Pearson, Philippa | 329 | EFT |
| Amoroc Doors | 199 | EFT |

Leave off the monthly run:

- Mrs Marlene/Georg Van Eeden. Cancelled. Invoice 3136 (7 Oct 2026, R439, cancellation month) is the last bill. She still owes R7,619. No further monthly invoice.
- Mr Ruandré Wessels. Owes R2,956. Not on the client page. Not a debit order. Leave the invoice as it is.
- Aljo van Vreden. R0. Do not invoice.
- Deleted customers already at zero (Steyn, Such, Sukhraj, Pereira, Dykman). Ignore.
- Aerial Networks and Arial Networks. Separate companies, EFT only, out of this run.

Hundermark’s older invoices (through mid-2026) are R299. Pay the open invoice’s own amount. New months are R329.

Whale Rock Lodge is paid up. Her next invoice is 17 November. She stays EFT until a Netcash batch line exists for her. The 2 November batch of 15 does not include her. Do not add her to it from this note. `WHALE_DO_START` in `qb_api.py` is 1 November 2026 and means “first debit order from November”, not “she is already on the 2 November file”.

## What 17 October 2026 closed

Debit-order collections for years had been booked only as the lump transfer into FNB. Client invoices in QuickBooks stayed open. The client page already showed those collections as paid.

Before any QuickBooks write, a snapshot was taken:

`/root/backups/2026-10-17-before-netcash-qb/`

It holds `upp.db`, `accounts.json`, `clients.html`, the book CSVs, the QuickBooks customer / invoice / payment / account dumps, the account 79 general ledger (end balance −151,659.64), and `posted-payments.jsonl`.

### Catch-up debit orders

285 customer payments, ids 2170–2454, total R154,475.00. Each one:

- deposited to account 79
- dated the collection date
- applied to that month’s invoice
- note `Netcash D/O recon 2026-10-17 invoice {number}`
- skipped when the invoice was already paid, already linked, dated on or after 17 Oct 2026, or the collection amount was not the open balance

Account 79 moved from −151,659.64 to 2,815.36. That R2,815.36 is the gap between client receipts, fees, interest, and transfers already on the ledger. It was not journaled to zero.

Fees already on the books at that point: account 87 R4,893.11, account 89 R7.28, account 88 R0.35. Transfers to FNB account 78 were −166,657.38, with further deposits out to FNB of −10,040.22. Payments already on account 79 before this catch-up were R29,938.

Unpaid named debit orders were not posted. The only ones in the books were G Cupido R759 on 4 May, 3 Aug, and 1 Sep 2026.

### Same-day checksum

Four customers still disagreed with the page. Each fix uses a real invoice or a real collection.

| Client | Was | Now | What was posted |
|---|---:|---:|---|
| Phillip De Gruchy | 2,218 | 1,219 | Payment 2455, 1 Nov 2024, R999, account 79, invoice 2431 (id 1061), batch 20241101. The December 2024 R999 was already on invoice 2441. Open invoice is 3142. |
| Annette Bing HH | 429 | 439 | Invoice 3140 (id 2151) raised from R429 to R439. June–September 2026 invoices were already R439. Not emailed again. |
| Van Eeden | 7,180 | 7,619 | Invoice 3136 (id 2456), 7 Oct 2026, R439, cancellation month, not emailed, left unpaid. |
| G Cupido | 2,277 | 759 | EFT links moved, 5 Oct debit order posted, duplicate invoice voided. Detail below. |

Cupido’s 8 September EFT R1,950 and 6 October EFT R760 were already in QuickBooks on FNB. Amounts and bank account were left as they were. The lines now sit on the invoices the client page had already reconciled:

| Payment | Date | Amount | Now applied to |
|---|---|---:|---|
| 2090 | 8 Sep 2026 | 759 | Invoice 3074 (unchanged) |
| 2091 | 8 Sep 2026 | 232 | Invoice 3013 (was duplicate 3055) |
| 2088 | 8 Sep 2026 | 200 | Invoice 3013 (was 3106) |
| 2089 | 8 Sep 2026 | 759 | R432 on 3101, R327 on 3013 |
| 2136 | 6 Oct 2026 | 527 | R327 on 3101, R200 on 3106 (was 3125) |
| 2135 | 6 Oct 2026 | 233 | Invoice 3130 (unchanged) |
| 2457 | 5 Oct 2026 | 759 | Invoice 3125, account 79, batch 2571994, paid |

Invoice 3055 (id 1979) was voided. It was created 35 seconds after 3054, same fibre line, same R759. 3054 is the June invoice the 1 July debit order paid. The May, August, and September unpaid debit orders were not marked paid. Those invoices were settled by the EFTs above. His only open invoice is 3150, R759.

Before-images of payments 2091, 2088, 2089, and 2136, and of invoices 1979 and 2151, are in `checksum-2026-10-17/` under the snapshot directory. New payment ids are appended to `posted-payments.jsonl`.

Account 79 after the two extra collections (R999 and R759) is R4,573.36. Still not journaled to zero.

### Balances that match the page

| Client | Due |
|---|---:|
| Amoroc Doors | 199 |
| Bing Noordhoek Fibre | 599 |
| Annette Bing HH | 439 |
| Bryant Michael | 759 |
| Phillip De Gruchy | 1,219 |
| Dirk De Villiers | 399 |
| Jean de Villiers | 550 |
| GeoCorp | 759 |
| HPP Control Room | 599 |
| Havenga | 699 |
| Hermanus Builders | 759 |
| Stan Hundermark | 329 |
| Lategan | 999 |
| Derek van Zyl | 759 |
| G Cupido | 759 |
| Gordon Neethling | 759 |
| Phillipus May | 439 |
| Murray DH | 759 |
| Paltco | 2,798 |
| Pearson, Philippa | 329 |
| Van Eeden | 7,619 |
| David Wantling | 439 |
| WCC Tech | 1,000 |
| Whale Rock Lodge | 0 |
| Mr Ruandré Wessels (not on the page) | 2,956 |

Paltco’s R2,798 is invoice 3134 plus 3111. Van Eeden’s R7,619 is the arrears plus 3136.

## Every day — FNB from QuickBooks

Do this once a day. Fetch the FNB register from QuickBooks (account 78). Use the General Ledger for that account. A TransactionList report with a columns override returns the whole company and is not the register.

Token refresh is `access_token()` in `/root/gowifi-upp/qb_oauth.py`. It rewrites `/root/secrets/qbo.token` only.

For each new FNB line since the last logged row:

1. **Client EFT.** One bank credit is one receipt. Log it. Apply it to that client’s open invoices, oldest first, then to any “D/O return · collect EFT” line. Deposit account stays 78. The payment total stays the bank amount.
2. **Expense.** An FNB debit that is not the Netcash transfer is logged to the expense account already used for that payee. It does not go onto a client.
3. **`NETCASH …NETCASH`.** Transfer from 79 to 78. Log it on both accounts. Do not create a client payment.

After the new lines are applied, each customer’s QuickBooks balance must still equal the client page. If it does not, stop and report the name, the page due, and the QuickBooks balance. Do not add a receipt to force the match.

Where a debit order is unpaid, look for a later EFT that is not already linked. Apply that unused EFT. Leave the invoice open when the EFT is already fully applied somewhere else. Cupido’s May, August, and September unpaids are the pattern: the September and October EFTs were real, and they were already fully used.

## Every month — invoices on the 17th

This is the short run. One invoice per name in the standing list, except the names under “Leave off”.

1. Read the standing table above. Skip anyone who has ceased, is at R0, or is Wessels.
2. In QuickBooks, copy that client’s latest real invoice: same customer, same item, same description, amount from the standing table. Date it the 17th. Due date the 17th. Income account 69.
3. Annette Bing HH is R439. Hundermark’s new month is R329. De Gruchy is R1,219.
4. Skip the client if QuickBooks already has an invoice for them dated that 17th.
5. Email it the same way the October invoices were emailed. Do not email a cancellation.
6. Leave the new invoice unpaid. The debit order or the EFT pays it later.
7. The client page and the QuickBooks balance both go up by that invoice. They must still match.

The October 2026 invoices (dated 17 Oct) stay open until the November collection or an EFT. Do not pay them as part of creating the next month.

## Debit order — action date, then two more days

The action date is the date the batch is set to run. For November 2026 that date is 2 November (15 lines, R9,976 authorised). A normal month is the 1st.

Pull Netcash read-only: `python3 /root/gowifi-upp/netcash.py pull`. On 17 Oct the service key was empty and the SOAP call returned AuthenticationException. Historical rows came from the masterfile. Do not upload a batch to make the pull succeed.

A line counts only when it has a batch id and an account ref. A name on a list is not a debit order.

Late check, using 2 November as the example:

1. **2 November, late afternoon.** Pull Netcash. If the batch has no processed paid or unpaid result yet, change nothing in QuickBooks.
2. **3 November.** Pull again. Same rule.
3. **4 November.** Pull again. If a line still has no processed result, alert. Do not post a payment for it.

A processed **unpaid** is a finished result. Post no payment. Leave that invoice open. Show it as unpaid. Alert only when the result is still missing on the third calendar day (action date plus 2).

## When the batch result is in

Same day the paid and unpaid results are back:

1. **Paid.** One customer payment per line. Date is the collection date. Amount is the amount Netcash took. Deposit account 79. Apply it to that month’s invoice, and only when the amount equals the open balance. Note `Netcash D/O recon {today} invoice {number} batch {id}`. Append the payment id to `posted-payments.jsonl`. Skip an invoice id already in that log.
2. **Short collection.** If Netcash took less than the open invoice (Annette’s authorised line may still be R429 against invoice 3140 at R439), post the amount collected and leave the difference open. Do not invent the difference. Report the client and the gap.
3. **Unpaid.** No payment. The invoice stays open on the page and in QuickBooks.
4. **FNB settlement.** Look in QuickBooks for the `NETCASH` deposit on account 78 and the matching transfer out of account 79. It often lands a banking day or two after the collection. If it is not there yet, note it and pick it up on the next daily FNB fetch. Do not create the transfer.
5. **Account 79 for the month.** Prior balance, plus client receipts posted above, plus interest income (88), minus service charges (87), minus interest expense (89), minus the transfer to FNB. That is the Netcash account balance. Do not journal it to zero to match a guess. A monthly tie to the Netcash statement needs that statement’s ending balance. None was loaded on 17 Oct, which is why R4,573.36 still sits on account 79.
6. **Checksum.** Every client on the page: page due equals QuickBooks customer balance. The new 17th invoice is the open bill when the collection has cleared the previous one. Wessels stays as he is.

## Restore

Box files, only if the local database or the published page was overwritten: copy `upp.db` back to `/root/gowifi-upp/upp.db` and `accounts.json` back to `/home/user-data/www/default/dash/accounts.json`. The snapshot is from before the 285 payments, so restoring it also drops later local edits. Prefer undoing the QuickBooks documents.

QuickBooks payments to void if the whole catch-up has to come off: 2170–2454, plus 2455 (De Gruchy) and 2457 (Cupido 5 Oct). Void only ids that are not in the snapshot’s `qb-payments.json`.

Cupido’s EFT line edits go back from `checksum-2026-10-17/payment-2091-before.json`, `payment-2088-before.json`, `payment-2089-before.json`, and `payment-2136-before.json`.

Invoice 3055 was voided and cannot be unvoided. Leave it voided. It was a duplicate of 3054.

Annette’s invoice 3140 stays at R439 because the page is R439. Van Eeden’s invoice 3136 stays because the page includes it.

## Next dates

| When | Do |
|---|---|
| Each day | FNB register from QuickBooks. Apply new EFTs and expenses. |
| 2 Nov 2026, late afternoon | First Netcash pull of the batch set for that day. |
| 3 Nov 2026 | Second pull if 2 Nov was not processed. |
| 4 Nov 2026 | Third pull. Alert if a line still has no processed result. |
| The day results are in | Post paid, leave unpaid, look for the Netcash-to-FNB transfer, tie account 79, checksum the page. |
| 17 Nov 2026 | Next monthly invoices, from the standing list. |
