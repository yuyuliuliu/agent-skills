# Agent Skills — Field-Tested Skills for AI Coding Agents

Practical, battle-tested Agent Skills (per the [agentskills.io](https://agentskills.io) specification) distilled from running a real one-person AI company: a multi-session AI operation that produces short-video content for local restaurants, analyzes customer feedback, and maintains its own knowledge base.

Every skill in this repo has been used in production, not written from imagination. The real cases, real numbers, and real failure modes are the point.

## Skills

### 1. `data-semantic-guard` — stop misreading table labels as business facts
Spreadsheets from handwritten logs, screenshot OCR, or external imports often have headers whose surface text lies (a "color" column that is really a day-count marker). This skill forces the agent to: suspend literal interpretation → verify with the user → run numeric sanity sweeps (text-numbers silently skipped by SUM cost us ¥30,765 once) → classify fund nature before any financial model → add anti-misread annotations so the mistake can never recur.

**Includes**: OCR/photo trap reference, numeric sweep code patterns, Excel file-lock workarounds, and a parameterized annotation script.

### 2. `methodology-to-rules` — land a methodology document as *executable local rules*, not dead documentation
When someone hands you an engineering constitution or process spec, copying it wholesale buries the operator; summarizing it to death strips the teeth. This skill lands the document as triage: archive the original verbatim, cut using the document's *own* authorization sentence, bind every rule to the real environment (real paths, real commands, real past failures), de-duplicate against existing rule files, run a cross-document consistency check, and surface every conflict to the human.

**Includes**: the full procedure, anti-pattern table, output shape, and a real case where four documents were landed in one session.

### 3. `social-comment-insight` — turn raw scraped comment dumps into structured insight
Takes the vertical single-column comment dumps scraped from social platforms, parses the block structure, cleans and dedupes, labels sentiment/pain-point/need/category/priority with a rule-based NLP pass, and outputs: structured xlsx, an n8n-ready CSV, a chart-rich report, and the Top-3 problems most worth solving.

**Includes**: two runnable scripts (`analyze_comments.py`, `build_report.py`).

## Install

Copy a skill folder into your agent's skills directory:

- Claude Code: `~/.claude/skills/<skill-name>/`
- Codex: `~/.codex/skills/<skill-name>/`
- Other agents: follow the [Agent Skills spec](https://agentskills.io)

Or install across 9 platforms with [openskills](https://www.npmjs.com/package/openskills): `npm i -g openskills && openskills install yuyuliuliu/agent-skills`

## Related
- 中文完整版实战知识（TTS 引擎调教判决书等）在 [UUMit 知识商店](https://www.uumit.com) 搜索 "中文 AI 配音避坑包"。

## License
MIT © 2026. The real-case excerpts remain the property of their operator; please keep attribution links intact.
