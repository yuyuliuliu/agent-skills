---
name: data-semantic-guard
description: Use when processing user-provided spreadsheets that originated from handwritten/paper logs, screenshot OCR, or external imports—especially those with ambiguous dimension labels like color/date/category/status. This skill guards against misreading label literals as real business semantics by verifying true meaning, adding anti-misread annotations (cell comments + header note + header renaming), running numeric sanity sweeps, and handling Excel file locks.
---

# Data Semantic Guard

## Overview
Detect and prevent the trap of reading a table's label literals as their real business meaning. Handwritten/paper logs, screenshot-OCR'd sheets, and externally imported tables often carry labels whose surface text diverges from what they actually represent (e.g. a "颜色/color" column that is really a day-counting rotation marker, not dye color). This skill makes the agent stop, verify, annotate, and record—instead of silently propagating the wrong interpretation downstream.

## When To Use
Trigger this skill whenever the user hands over a table/spreadsheet (xlsx, csv, ods) that:
- Came from a handwritten or paper source, screenshot OCR, or external system export/import.
- Contains dimension labels easy to confuse with real semantics: color, date, category, status, type, grade, level, etc.
- Will feed analysis, formulas, or downstream reports where a misread label would corrupt conclusions.

## Workflow

### Step 0 — When the source is an image / photo (do this BEFORE Step 1)
Applies when the user hands over a **picture** instead of a spreadsheet: handwritten ledger photos, on-site whiteboard / production-board photos, machine nameplates, product photos.

- **Cross-check the picture against spoken context.** Whatever the image yields must be collided with what the user told you in words. If the two conflict, record BOTH as `conflict / pending-verification` and keep them side by side — never silently overwrite either side with the other.
- **State recognition confidence honestly.** Blurred text, cursive handwriting, glare / reflection, and fine color differences are failure modes that do **not** improve with repetition or with more domain context. Mark them `needs-human-verification` and say plainly "this one I can't read reliably" instead of guessing a value and writing it in.
- **Check field feasibility BEFORE designing a form.** Insights extracted from a photo often get turned into a form that floor staff must fill. Before building it, ask: "will the person on site actually fill this, every day?" If the attribution is multi-causal or fuzzy (real case: a dyer said "too many causes of vat-rejection to categorize"), downgrade to the lowest-burden metric (record the event + its cost only, cause left as free text for later clustering) rather than forcing fine-grained attribution that will never get filled.

### Step 1 — Suspend literal interpretation
Do not treat a header word as the dimension it names. Before any computation or structural change, scan every dimension label and ask: "Does this label's surface word match its true business meaning?" Flag any label that could be a proxy, placeholder, or rotation marker rather than a literal category.

**⚠️ Before processing handwritten / paper / photo / OCR tables, read `references/ocr-traps.md` first** — it is a field-verified table of known misread traps (edge-corner misread detection, confusion alerts). Starting without it is working blind.

### Step 2 — Verify true semantics with the user
When a suspected ambiguity is found, confirm the real meaning BEFORE editing. Use concrete options rather than assuming. Never silently reassign a label's meaning.
- Good: "Does the header 'red/blue/black' mean the actual dye color, or a day-counting rotation marker used in paper logging?"
- Bad: assuming "color" = dye color and building color-based analysis on it.

### Step 2.5 — Numeric sanity sweep (MANDATORY before trusting any total)
A cell that *looks* like a number may be text. Text numbers are **silently skipped** by SUM — no error, no warning, just a wrong total. This bit us once and cost a ¥30,765 understatement.

- Sweep every amount column first (code in `references/numeric-sweeps.md`, **required reading**), surface all text-numbers.
- Text-number rule: **never overwrite directly** (it may be an intentional split expression like `25765+5000`) — convert to the numeric sum, move the original split into a notes column, and present BOTH old and new totals to the user.
- In the same sweep, normalize date columns (uniform format) and check sequence gaps (backfill or flag; never guess the cause).

### Step 2.6 — Classify fund nature BEFORE building any financial model
Raw ledgers mix fundamentally different kinds of money. Dump them all into "income/expense" and every downstream metric is wrong. Before importing into a P&L, tag **every row** with a fund-nature class and decide explicitly whether it enters the P&L:

| Fund nature | How to recognize | Into cash flow | Into P&L | Example (real dye-factory ledger) |
|---|---|---|---|---|
| Operating revenue | Customer paying for real business | ✅ | ✅ | Customer payment (dyeing fee) |
| Pass-through / collect-and-forward | **Two directions of the same money**, paired on income and expense sides | ✅ | ❌ | "Pass-through" received ¥34,427 / paid ¥36,552 |
| Capital expenditure | Equipment, deposits, bulk materials — not current-period expense | ✅ | ❌ | Vat deposit ¥30,000, stainless steel tubing ¥12,500 |
| Misc / non-operating | Selling scrap, non-core | ✅ | ❌ | Cardboard scrap ¥460 |
| Unverified / unknown | Blank memo or self-contradictory amount | ✅ (tag "unverified") | ❌ | Blank-memo items ¥32,524, ¥4,180 |

**⚠️ "Pass-through" is the sneakiest class**: it appears in BOTH the income and expense sheets, looks like two entries, but is one sum of money going in and out.
- Detection: find the **pairing** — several income rows sum to one expense row + incidental costs (real case: 5,975+11,897=17,872 → expense 15,872 + printer 2,000, exact match).
- Disposition: it goes into cash flow (money really moved), but **never into revenue detail / cost detail** — otherwise revenue and costs are **inflated in both directions**.
- Use a separate category in the cash-flow sheet ("pass-through in" / "pass-through out") and **rewrite the summary-area formulas** — the original `SUMIFS(D,"<>dyeing-revenue")` was subtracting pass-through income as if it were an expense.

Also check: **is the P&L cash-basis or accrual?** Without unit prices you can only do cash basis, in which case:
1. State the basis prominently in the header — don't let anyone read "August loss ¥85,000" as fact
2. Switch customer reconciliation from "receivable − received" to "payments received × business volume", which actually exposes **customers with volume but no payment** better
3. Large fixed-amount payments (e.g. utilities billed across months) distort single months violently; exclude and annotate them explicitly in conclusions

**⚠️ Customer-name alignment across sheets (real pitfall, 2026-09-03)**: the same customer is often written differently in different sheets (invoice "当阳" / ledger "当"; full name / single-char abbreviation / place-name standing for a person). Before any cross-sheet `SUMIF`/`VLOOKUP` matching, **build a mapping table and have the user confirm it** — otherwise matching fails silently and the customer is misread as "zero payment".
- Disposition: standardize on the **ledger abbreviation** (guarantees cross-sheet hits), keep full name and place-name explanation in a notes column.
- Use the misses in reverse: customer names that fail cross-sheet matching are often **real findings** (off-ledger customer / new customer / misread), not noise to ignore.

### Step 2.7 — Date-matrix column sweep (off-by-one kills totals)
When daily/monthly data is laid out as a **matrix** (rows = customers, columns = dates), the column range is the most frequent silent-error point. Measured consequence: missing 1 column → one customer's volume computed as 6,556.6 kg instead of 6,821.6 kg (265 kg off), which then corrupted unit price, share, and the "payment black hole" conclusion.
- Iron rule: **read the header, count the columns, assert the count — never hard-code a column range** (code in `references/numeric-sweeps.md`).
- Same for row ranges: use `while` / non-empty checks to walk to the end; never write a fixed `range(6,20)`.

### Step 2.8 — Period mismatch (cash basis vs accrual)
Work done this month, paid two months later — normal for small processing shops. **Cash-arrival month ≠ business-attribution month.**
- Detection: a payment memo says "payment for month X" but the arrival date is a different month → period mismatch.
- Consequence: on cash basis, **the working month shows a fake loss and the collection month a fake profit — both wrong** (real case: cloth dyed in July, paid in Aug/Sep → July −3,350, August −84,876, neither believable).
- Disposition:
  1. Add a cell Comment noting "cash belongs to month X / business belongs to month Y"
  2. State prominently that the sheet is **cash basis**, with "monthly P&L is for cash-flow reference only until accrual basis is adopted"
  3. **Never back-derive a unit price from "payments ÷ volume of the month"** — payments accumulate across months and may be partial. Measured: derived unit prices for paying customers ranged 0.71–62.23 CNY/kg, a **88× spread**. That "unit price" is meaningless.

### Step 3 — Add anti-misread annotations (after confirmation)
Once the true meaning is confirmed, annotate so future readers (and future AI sessions) cannot repeat the misread:
- **Header/title note**: append a clarification sentence to the sheet's top description cell.
- **Cell comment**: attach an openpyxl `Comment` to the first occurrence of the ambiguous label (e.g. the first "红" cell), explaining the real semantics.
- **Rename if needed**: if the label name itself misleads (e.g. a "颜色" column that is actually a rotation marker), rename the header to a neutral term (e.g. "rotation marker") and add the comment.

Ready-made code patterns for writing (comment / rename / file lock / user-hand-edit diff) are in `references/editing-workbooks.md`.

### Step 4 — Handle Excel file locks
openpyxl `save()` fails with `PermissionError` when the target xlsx is open in Excel (Windows exclusive lock). The failure happens before any handle is taken; the original file is not corrupted (verified via `stat`). Workaround: write a `-preview` copy → user closes Excel → write back to the original → clean up the copy. Back up before writing (details in `references/editing-workbooks.md`).

### Step 5 — Persist the finding
Record the ambiguity and its resolution in the project's log file and in memory, so the lesson survives across sessions.

## References (loaded on demand, not expanded here)
| File | When to read |
|---|---|
| `references/ocr-traps.md` | **Required before processing handwritten/OCR tables** (Step 1) |
| `references/numeric-sweeps.md` | Required before any total/share computation (Step 2.5 / 2.7) |
| `references/editing-workbooks.md` | When writing Excel / diffing user hand-edits (Step 3 / 4) |
| `scripts/add_antimisread_annotation.py` | Parameterized reference implementation: comment + annotation + optional rename, backup first, preview-copy against file locks |

> Note: `references/` retain real-case content in Chinese (a working dye-factory ledger). The patterns are language-agnostic; the Chinese is evidence, not a requirement.
