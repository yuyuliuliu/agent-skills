---
name: methodology-to-rules
description: Use when the user pastes a long methodology/spec document (AGENTS.md, AI_USAGE.md, role-play prompt, engineering constitution, workflow spec) and wants it "added to the project" or "made into rules". This skill prevents two failure modes — (1) copying the document wholesale, which buries a near-beginner under enterprise-grade process, and (2) fabricating details the document itself forbids inventing. It lands the document as a locally-executable rule file bound to the user's real environment, archives the original verbatim, and de-duplicates overlap with existing rule files so rules live in exactly one place.
agent_created: true
---

# Methodology → Local Rules

## When To Use

Trigger when the user pastes a long document and the intent is to adopt it:

- "把这个纳入项目" / "加进宪法" / "这是给你看的" / "存起来" ("adopt this into the project" / "add it to the constitution" / "this is for you" / "keep it")
- Engineering constitutions: AGENTS.md, CLAUDE.md, GEMINI.md, Cursor rules
- Process specs: AI_USAGE.md, design-package workflows, audit checklists
- Role-play framework prompts: "you are a chef / architect / reviewer, follow these N steps"

**Do NOT trigger** for: short factual notes, code snippets, one-off instructions, or documents the user is asking you to *answer questions about* rather than adopt.

**Language note**: trigger phrases and real-case excerpts are kept bilingual (Chinese + English) — the original operator works in Chinese; the patterns are language-agnostic.

## The Core Problem

These documents are written for mature engineering teams. A solo builder with near-zero technical foundation, aiming at first revenue within weeks, will abandon the work within two days if the full spec is applied. But the document is not worthless — most of it constrains **the agent**, not the human. The human never needs to read it.

So the landing is never "copy the file". It is **triage**.

## Procedure

### Step 0 — Classify before touching anything

| Question | Determines |
|---|---|
| Does the document constrain the agent or the human? | Agent → goes to the AI layer, human never reads it. Human → must be short enough to actually read |
| Does it require facts that don't exist yet (project name, stack, commands, owner)? | If yes → **do not generate the artifact**. Land the process, leave placeholders as `待定` |
| Does it explicitly forbid acting without input? | **Obey it.** "没有目标项目事实就不许生成项目级宪法" means generating one is fabrication, and fabricated rules mislead future sessions |
| Does it overlap an existing rule file? | If yes → de-duplicate in Step 4 |

### Step 1 — Archive the original verbatim

Always write the full original into an `附录-*.md` file or an appendix section of the new file. **Never delete or rewrite the original.**

Reason: clauses that are useless today become correct later. Multi-agent work, i18n, RLS, codegen — all irrelevant now, all relevant at scale. The archive is where you retrieve them from.

### Step 2 — Cut using the document's own rules

**Find the sentence in the document that authorizes cutting it.** Almost every engineering spec contains one. Examples:

- "若某条不适用于当前项目，应删除或替换，而不是保留成空口号"
- "只启用目标项目真实使用的 STACK 和 ADAPTER 规则"
- "删除不需要的模板残留、泛化口号、重复条款"

Quote that sentence back to the user when explaining what you cut. It converts "I ignored part of your document" into "I followed your document's own rule for ignoring it".

**Log every deletion with a reason** — a table of `删掉的 | 为什么`. Deletions must be auditable and reversible-by-reading.

### Step 3 — Bind to the real environment

Generic advice is useless. Every landed rule must point at something concrete:

| Generic | Bound |
|---|---|
| "use a venv" | `python -m venv venv`（写明用哪个解释器，不用含糊的"用虚拟环境"） |
| "don't use an empty shell interpreter" | 禁用空壳解释器（无 python.exe 的安装目录） |
| "don't leak keys" | `.env` 进 `.gitignore`，不进网盘 |
| "verify before claiming done" | 贴实际跑过的命令和输出 |

Also pull in **the user's own past failures** as concrete examples rather than inventing generic ones. A rule illustrated by a mistake they personally made gets remembered; a rule illustrated by a hypothetical gets skipped.

### Step 4 — De-duplicate against existing rule files

This is the step everyone skips and it is the one that matters most.

When a new file overlaps an existing one, **apply the document's own single-source rule**: one file owns the detail, the other keeps a summary plus a pointer.

```
旧文件：保留 N 条要点 + 「⚠️ 详细流程不在本文件，切到 XX」
新文件：拥有全部细节
```

Never write the same procedure fully into two files. Two copies drift within weeks, and then nobody knows which is authoritative.

Add the new file to the parent index's structure table, and state the pointer relationship in that index too.

### Step 4.5 — Run a cross-document consistency check

Only after two or more documents have landed. **Documents contradict each other, and contradictory rules are worse than no rules** — the next session picks whichever one it reads first.

Write the check into an `附录-文档一致性检查.md` (or an equivalent section). It must contain:

| Section | Contents |
|---|---|
| Document inventory | file, source doc, what it governs, status |
| Entry-point map | which file hands off to which, so none of them duplicate detail |
| **Conflict list with verdicts** | each conflict + the ruling + the condition that would reverse it |
| Confirmed-consistent items | what was checked and found clean (equally valuable — proves the check happened) |
| Pending placeholders | what stays `待定` and what fact would unblock it |
| Open questions | what only the user can answer |

**Look specifically for these three conflict types:**

1. **Stack conflicts** — doc A recommends a heavy toolchain, doc B assumes a light one. Resolve against the user's actual constraints, and record the *condition under which the heavy one becomes correct* ("not rejected, deferred").
2. **Missing preconditions** — doc A starts at a step that doc B treats as a prerequisite. The later doc often reveals the earlier one skipped something (e.g. "draw the pages" without first fixing web vs mobile vs mini-program).
3. **Process-vs-person conflicts** — the most dangerous kind. Docs demand N confirmation gates; the user's known failure mode is abandoning things midway. **Say so.** Propose compressing gates and explain what must not be compressed. Generic specs assume a patient user; a solo builder racing a revenue deadline is not that user.

### Step 5 — Record state honestly

End the file with a status table. `未开始 —— 无目标项目` is a valid and correct state. Do not fabricate progress.

Add a row to the parent file's `修改记录` table: date, what changed, **why**.

### Step 6 — Surface the conflict to the user

Do not silently downgrade the document. Say plainly:

1. What you cut, and the document's own sentence that authorized it
2. What you refused to do, and the document's rule that forbade it
3. What stays `待定` and what fact would unblock it

## Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| Copy the document into the repo unchanged | Beginner abandons it. Also imports rules for tech the project doesn't use |
| Fill `@@PROJECT@@` / `@@STACK@@` from experience | The document forbids it. Filled placeholders become facts future sessions trust |
| Summarize so aggressively the rules lose teeth | Losing "must stop and ask" / "no patch-style fixes" defeats the whole point |
| Write the procedure into two files | Drift. Within weeks neither is authoritative |
| Generate the artifact when the document forbids acting without input | Fabricated rules are worse than no rules — future sessions trust them |
| Skip the appendix archive | Clauses needed at scale are gone forever |

## Output Shape

A landed rule file contains:

1. **Scope line** — one sentence on what this file governs
2. **Relation table** — how it differs from adjacent rule files (when overlap exists)
3. **Preconditions** — what must be true before this file applies
4. **The process** — steps, each with its deliverable and gate
5. **Concrete tables** — bound to real paths, real commands, real past failures
6. **Status table** — honest, `未开始` is acceptable
7. **Appendix** — original text, verbatim
8. **修改记录** — date / what / why

## Reference Landing (real case, 2026-09-03)

Four documents landed into `代码项目\宪法\` over one session:

| File | Source doc | Cutting decision |
|---|---|---|
| `05-agent行为宪法.md` | Engineering-grade AGENTS.md | Cut multi-agent, PR contribution, codegen, i18n, RLS, MQTT/WSS. Kept: agent must say no, reasoning gate (7→5 questions), no patch-style fixes, error severity tiers, verification rules, must-stop-to-ask list, handoff rules |
| `06-立项流程.md` | AI_USAGE.md | Landed the process; **refused to generate any project AGENTS.md** because the doc forbids it without project facts |
| `07-建库三阶流程.md` | Chef/critic framework prompt | Kept the UI→DB→API ordering as a hard rule. Filled zero placeholders |
| `08-后端设计流程.md` | Backend five-step prompt | Overlapped 07's stage three → **07 stage three demoted to a pointer**, 08 owns all backend detail |
| `09-前端设计流程.md` | Frontend five-step prompt | Recommended React/Vue + TypeScript — **directly contradicted the user's own earlier decision to keep node_modules out**. Overrode it in-file with an explicit ruling plus the condition that would reverse it. Overlapped 07's stage one → demoted to a pointer |
| `附录-文档一致性检查.md` | (meta, no source doc) | Written after the fourthdoc landed. Found a stack conflict, a missing precondition, and a process-vs-person conflict |

Each kept its original in an appendix section. Each recorded what was cut and why. All four were indexed in `00-宪法总纲.md`.

**The recurring move:** every one of these documents contained the sentence that authorized cutting it. Finding that sentence is what makes the landing defensible instead of presumptuous.

**The move that mattered most:** the fifth document recommended a toolchain the user had already ruled out for a stated reason. Catching that required holding the earlier decision in mind, not just processing the new document in isolation. When landing document N, re-read what documents 1 through N-1 already decided.
