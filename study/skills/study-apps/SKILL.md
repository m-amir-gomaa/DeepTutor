---
name: study-apps
description: Maintain simple linked Obsidian notes and small source-grounded Anki card batches through the configured study tools, using real app interfaces when useful.
---

Use the tools that are actually mounted. SKILL.md instructions do not import
Codex's connectors or executable capabilities. Discover/load the selected
study-vault service and Anki service when their schemas are needed.

Obsidian uses ordinary Markdown files in the selected vault. `save_note` creates
versioned generated notes through a transactional outbox, preserving manual edits
and existing STATE prose. Native Obsidian and Neovim see those same files. For a useful static vector
artifact, `vector_concept_card` invokes the installed CLI-Anything Inkscape harness.
Do not invent a CLI-Anything harness for an application or claim that a skill alone
installs it. Additional app capabilities need deliberate installation and a real
operation check before use.

Anki is the recall scheduler. Use the existing `Study Concept` note type with
fields Prompt, Answer, Why, Source, Track and Key. The track/deck is given by
orientation: `Study::<selected vault name>`. Source should retain book/edition,
section/PDF page or official documentation URL and the linked vault note.
Use a stable Key and check `find_notes` before adding a duplicate. The installed
AnkiMCP service limits batches to five notes; use small batches after meaningful
units. Card creation/organization is owner-authorized without repeated approval.
Anki fields are HTML, not Markdown. Use `<code>`, `<br>` and lists sparingly;
use Anki's `\( ... \)` and `\[ ... \]` MathJax delimiters, never dollar math.
Make the source note a clickable `obsidian://open?path=...` link using the
percent-encoded absolute vault-note path. Keep the book/edition/page visible.

Write one clear retrieval target per card. Use short answers, a useful reason or
counterexample, code/figure context when needed, and the source. Avoid giant
cloze dumps, ambiguous prompts and cards that merely repeat a paragraph. For
algorithms, cards support definitions/invariants/trade-offs; independent coding
and proof practice remain separate. Treat new cards as unlearned.
Use only the current unlocked unit. The prepared first-part cards are already
imported; reuse their stable Keys and do not create a second paraphrased batch.
Before adding a new batch, check factual accuracy against the actual source,
read the prompt without its answer to catch ambiguity, inspect rendered simple
HTML/MathJax and check exact-Key duplicates. Queue validation enforces concise
fields and rejects Markdown code fences/dollar math, but semantic review remains
the tutor's responsibility. Preserve real review history and ratings.

Inspect the native FSRS configuration; preserve existing learner scheduling and retention preferences. Installation does not establish that FSRS is enabled.
That is the initial configuration; inspect get_fsrs_params when diagnosing
settings and preserve any later owner changes rather than forcing these defaults.
The learner supplies review ratings in Anki. Do not rate cards, fabricate review
events, optimize parameters without actual history, rewrite scheduling state,
delete notes, sync an account or change unrelated decks. A source correction can
propose a new card version while preserving old learner work.

At a useful unit boundary, give a short handoff: the source section, note title
and vault-relative path, cards actually added and their deck, the unanswered
check or next step, and any real tool failure. Suggest native Anki when recall
review is useful; suggest Obsidian when inspecting/editing linked notes is useful.
The owner should not copy the lesson between apps. Do not claim a GUI window was
opened or a deep link was tested without an actual supporting operation.

Prefer the scoped `queue_cards` then `sync_cards` tools for new batches. These
maintain a durable outbox, inspect exact stable Keys before adding, and reconcile
retries after a timeout. Track/deck are bound to the selected subject. A conflicting
existing card is preserved and surfaced; do not invent a new Key just to hide it.
Anki must be open for delivery. If unavailable, proposals remain pending;
explain that the local study launcher opens it and retry sync later. Keep teaching.
The original native Anki tools remain for reading actual review/settings data.
Use library/STUDY-SYSTEM-GUIDE.md for book-intake and app-navigation questions.

Use `app_links` for exact vault-note/source handoffs. Its editor argument list
does not open an embedded terminal. Native Anki's deck selection is the fallback
if a search URI is unsupported. Use `save_checkpoint` to retain the actual
pending question and next action. Generated assets are copied into the vault's
visuals/assets folder for offline viewing; quote the tool's absolute web URL in
chat. A card proposal is still not an imported card until sync confirms its outcome.

Imported store skills are supplementary. Owner preferences govern the language,
complete content/examples first, short checks after meaningful units, small
automatic card batches. Never adopt an imported skill's prerequisite interview,
daily reminders, bulk deck quota, OpenRouter generation, external upload or
new paid provider without the corresponding owner request. For critical reading,
use paper-reading-notes/scientific-critical-thinking only when actually assigned
and their supporting references can be loaded. Save research notes through the
scoped service in this subject. Missing data stays missing; do not fill it with
invented effect sizes or clinical grading outside its applicable context.

Current CLI additions: Browser runs DOMShell 2.0.10 in an isolated study browser,
with a retained lane per vault. It has no owner's Firefox account cookies and is
limited to localhost and the configured official JS/TS/React/Next docs domains.
Use cli_browser help and actual returned accessibility paths, never invented IDs.
Do not detach its lane or broaden domains to evade an access failure.
Obsidian Agent CLI supports filesystem note reads/writes with this vault's config;
the other Obsidian CLI requires its native Local REST API plugin. That server is
loopback-only and available while the corresponding Obsidian vault is open.
Core note/card tools do not require that GUI. Never print local API credentials.
Inkscape PNG/PDF now invokes real pinned Inkscape 1.4.4 and verifies the bytes;
the scoped vector card tool also uses that native renderer. LibreOffice 1.0.1
still requires an explicit docx/pdf preset. These are qualified operations, not
automatic certification of every plugin/backend feature listed by a CLI.

Mermaid SVG/PNG rendering now uses local Mermaid CLI 12.0.0 and Chromium; do not
send private diagram content to a public renderer. Draw.io 32.4.1 exports through
an isolated authenticated Xvfb display with a temporary app profile. Both now
have real image-byte checks; Draw.io PDF and Calibre EPUB-to-text also pass.
For every CLI, inspect metadata.exit_code and stderr as well as ToolResult.success:
the latter means the tool delivered an application response, not that the command
succeeded. Inspect/reopen actual output before calling an export complete.
Use read-only card statistics for setup checks. Never bury/skip cards or start a
review queue merely to inspect integration health; review choices belong to the
learner. Use native write_memory only for explicitly stated durable preferences.
Unit progress and real attempts remain in this vault's checkpoint/evidence ledger.

For primary-paper research through native exec, imports now support PyMuPDF and
Beautiful Soup. Tool output is bounded: inspect one paper at a time, print small
Methods/Results excerpts with section/page locators, and check truncation before
synthesizing. Several large full texts in one tool output can hide a later paper.
Fetch the missing section rather than replacing it with a search snippet or
implying that every source in the bibliography was actually inspected.
alphaXiv's four selected read tools and bioRxiv's seven tools have real operation
checks. Biology has bioRxiv assigned. Distinguish preprint versions, linked journal
publications and omitted tables. Existing connected OAuth grants should be reused;
do not trigger Reauthorize for a routine research request or health check.
