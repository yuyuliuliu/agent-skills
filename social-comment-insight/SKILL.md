---
name: social-comment-insight
description: Analyze raw social media/user comment Excel dumps. Parse vertical single-column scraped comments, clean, extract pain points, needs, sentiment, category tags and priority, then output structured tables, charts and a professional Markdown/HTML report. Use when the user asks to analyze batch comments, do pain-point mining, sentiment classification, or prepare structured data for n8n/dashboards.
agent_created: true
---

# Social / User Comment Insight Analysis

## When To Use
- The user uploads an Excel containing raw comments scraped from social platforms (TikTok/Douyin, Xiaohongshu/RED, Bilibili, etc.) — single-column, each comment followed by metadata rows (date / likes / shares / replies / username).
- The ask includes: deduplication, removing noise comments, extracting pain points / needs / sentiment / category / priority per comment, outputting a structured table, Top pain-point/need/keyword statistics, a professional report, and an n8n-ready CSV.

## Analysis Dimensions
- **Sentiment**: positive / neutral / negative, intensity weak / medium / strong.
- **Type**: pain point (negative) / need (contains demand words like "hope / need / can you / looking for / suggest") / neutral feedback.
- **Category tags** (multi-label):
  UX & interaction, usability, features, performance, content quality, professional reliability, security & privacy, cost & efficiency, ecosystem integration, industry adoption, ethics & society, other/general.
- **Priority**: scored on "category severity × frequency + likes/engagement + negative sentiment", bucketed high / medium / low.

## Workflow

### Step 1 — Parse raw comments
- Read the first column of the Excel (or a user-specified column).
- The file usually has two parts:
  1. A front section that may be a hand-edited "pain point / need list", variable length.
  2. The actual raw comments, typically in vertical blocks:
     ```
     [comment text]
     [relative time · region]   ← anchor row
     [like count]
     Shares
     Replies
     [expand N replies] (optional)
     [blank line]
     [username]
     ...
     ```
- Anchor on date rows matching the regex `^(.+?)(ago|yesterday|just now)[·：:]` — take the comment text above, the username and like count below.
- If the source has a different structure (e.g. already one clean comment per line), skip this parser and read line by line.

### Step 2 — Clean
- Remove blank rows, pure punctuation/emoji rows, single-character comments.
- Remove ads / spam (contains "add my WeChat", "DM me", "follow me", "essay writing service", etc.).
- Deduplicate: by the string stripped of punctuation and whitespace, keep the first occurrence.
- Normalize comment text: strip links, `@mentions`, `#hashtags#`, extra whitespace.

### Step 3 — Rule-based NLP labeling
- **Sentiment**: Chinese positive/negative lexicon + negation-word inversion + strong-negative-word detection.
- **Category**: keyword mapping onto the 11 categories; unmatched → "other/general".
- **Pain point / need extraction**:
  - Negative comment → pain point = first sentence; need = "—".
  - Contains a demand word (hope/need/can you/suggest/looking for/expect) → need = content after the demand word; pain point = "—".
- **Keywords**: jieba tokenization + stopword filtering.
- **Priority**: composite score of "category severity + log(likes) + negative weight", bucketed by percentile.

### Step 4 — Statistics & conclusions
- Sentiment distribution, type distribution.
- Top pain-point categories (ranked by frequency × severity).
- Top need categories (by frequency).
- Top 20 high-frequency keywords.
- Category co-occurrence matrix (which problems appear together).
- **Top 3 most-worth-solving problems**: the 3 highest-priority pain-point categories, each with "value of solving" and "business opportunity".

### Step 5 — Output
Under `analysis_output/`, generate:
- `{topic}_structured_data.xlsx`: full-field detail table.
- `n8n_ready.csv`: core fields `comment, pain point, need, sentiment, priority` (directly readable by n8n).
- `comment_analysis_report.md` + `comment_analysis_report.html`: professional report with charts.
- `charts/*.png`: sentiment distribution, category distribution, keywords, pain point vs need, co-occurrence matrix.

## Bundled scripts
- `scripts/analyze_comments.py`: runs Steps 1–4 (parse / clean / label / statistics), outputs `_df.pkl`, `summary.json`, xlsx, csv.
- `scripts/build_report.py`: builds the report and charts from `_df.pkl` + `summary.json`.
- Copy both scripts into your workspace, then adjust in-script `SRC` (input Excel path), `BASE` (workspace path), `start` (first raw-comment row; default 312) and re-run.

> Note: the bundled scripts ship with this skill's GitHub repo. The rule-based lexicon targets Chinese comments; the workflow is language-agnostic but the lexicon is not — swap in a lexicon for other languages.

## Known limitations
- Classification is rule/lexicon based; irony, metaphor and polysemy can be mislabeled. For higher precision add an LLM semantic-verification pass.
- Column structures differ across sources — always inspect the file header and metadata-row pattern before parsing.
