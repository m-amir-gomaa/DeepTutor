# Agent setup contract for the standardized DeepTutor fork

Read the repository `AGENTS.md`, upstream `docs-for-dev/AGENT_SETUP.md`, this file
and `study/README.md`. Preserve existing installations, settings and learner
records. User instructions override examples. Do not import the author's private
paths, books, accounts, business catalogue, acceptance receipts or identity.

## Establish the learner and boundaries

Ask only what is missing: disciplines, immediate goals/exams/research questions,
actual books/editions, preferred language and editor, explanation depth, useful
visual formats, check frequency and available providers. Choose one editable
discipline profile per vault; medical study and research can be separate vaults
or an explicit combined syllabus. An available book is not an assigned course.
Prefer content and complete examples before checks unless the learner chooses
otherwise. Keep goals and preferences editable in `LEARNER.md`.

Credentials are owner actions. Never ask for tokens in chat, inspect unrelated
credential stores, copy Codex host grants or commit local settings. Use each
provider's native authorization and confirm successful status afterward. Never
change a model, enable paid APIs, raise spending limits, automate messages or
grant broader machine permissions merely to make a test pass.

## Install and initialize

Use the documented v1.7.1 source flow: Python 3.12, upstream full requirements,
editable install without feature wheels overwriting source,
`python -m pip install -r study/study-runtime-requirements.txt`, Node 22 frontend
dependencies/build. The fork carries its core fixes in source; do not apply
the author's old absolute-path runtime patch scripts on a fresh host.

Use a private `DEEPTUTOR_HOME` outside the checkout. Initialize DeepTutor, then
`python study/manage.py init --profile medicine --name "Medical study"` (or the
chosen profile). Add another vault using `--slug research --profile research
--name "Research"`. The management script must not overwrite existing learner
files or routes. Start the app, then `python study/manage.py attach`. Confirm
the created workspace IDs, tool descriptions, selected skills and preserved
existing resources. Connect missing services selectively; assignment alone is
not authentication. No embeddings or paid parser are required for local FTS.

The non-secret `installation.json` owns root paths, loopback origins, executable
paths and optional Modal metadata. Native auth stores own credentials. Use the
same configuration/runtime home for backend, management and scoped MCP child
processes. Do not silently fall back to the author's filesystem.

## Configure useful capabilities, not an indiscriminate tool list

All profiles share source access, notes, recall, memory, diagrams and checked
interactivity. Add only relevant tools, and report absent optional tools:

| Capability | Configuration and actual acceptance |
|---|---|
| Model | Owner authorizes provider and selects an available exact model; run one bounded real answer. Second Codex account is optional and separately authorized. |
| Books | Import an original one-page synthetic PDF first. Verify immutable copy/hash, physical page lookup, text index and isolation across two test vaults. |
| Course | Choose the actual book's introductory range. Keep later units locked. Route creation is planning, not learner evidence. |
| Memory | Store only explicit durable learner preferences in native profile/preferences. Read them back. Never seed accomplishments or patient data. |
| Obsidian/editor | Register each vault separately and open its shared Markdown. External Neovim is supported; embedded editor behavior is not provided. |
| Anki | Connect the local authenticated MCP service, configure Study Concept fields Prompt/Answer/Why/Source/Track/Key and Study::NAME deck. Read back one clearly labelled unreviewed fixture; never rate it. Preserve existing FSRS configuration. |
| Draw.io | Install native exporter; generate/reopen an original small map and inspect SVG/PNG plus relation labels. |
| Interactivity | Install `study/package.json` dependencies and a Playwright Chromium runtime. Run actual play/step/reset/input/keyboard and edge-case checks. A generated HTML string is not browser acceptance. |
| Animation | Install Manim plus FFmpeg/font dependencies in a scoped environment; use bubblewrap on Linux. Render/play a small original mechanism. No host-code fallback if isolation is unavailable. |
| Local OCR | Install the pinned MinerU 4.1.3 runtime/models, run the included local wrapper, compare a bounded synthetic scanned page and check ZIP/provenance/index updates. |
| Research | Medicine/biology: PubMed and bioRxiv; broader papers: alphaXiv; technical docs: Context7/DeepWiki. Connect through Personalization, perform one relevant read operation and check OAuth again after restart. Label preprints and uncertainty. |
| CLI apps/skills | Discover the installed in-app catalogue, inspect the actual instructions and selectively install. Core native media routes are supplied. Optional third-party harnesses need their own acceptance; do not assume the author's patched DOMShell/Obsidian clients exist. |

The initial portable local execution target is Linux. For other systems, document
which tools are unavailable and use a deliberate container/platform adaptation;
never describe untested native parity as complete. Do not globally disable
sandboxing or install system services simply to unblock an optional renderer.

## Optional Modal route

Keep cloud disabled until the owner selects a Modal workspace and confirms the
current credit and spending policy. Install the isolated SDK from
`study-modal-requirements.txt`, use native browser authorization and set only
non-secret app/profile/policy values in configuration. Deploy the private
`modal_mineru_app.py`; it exposes no public web endpoint and creates no scheduled
or permanently running worker. Check metadata without OCR first. Only with
authorization run one original synthetic scan through the shared pipeline.

Keep one-page input/size/time/concurrency limits, immutable originals, validated
ZIPs, provenance and correction-preserving cache. Retain reservations for failed
admitted jobs. Do not reuse the author's public guest service or reset admission
data. Report metering delays and distinguish conservative reservation caps from
actual billing. Changing profiles may point at a different workspace/deployment.
Do not silently upload a failed local job or change backends on failure.

## Verify and hand off

Run the portable unit/fixture suite and the relevant upstream checks. Record
installed/configured/authenticated/exercised separately in private
`.control/readiness.json`, with the actual date, versions and evidence paths.
Do not copy the author's 77-test/live-provider acceptance into a fresh learner's
readiness. Test affected native Chat/Solve/Quiz/Research/Visualize/Video/Audio
paths as authorized; source fields, browser completion and playback are distinct
checks. Never manufacture learner answers to satisfy a route gate.

Prepare one chronological opening unit, source-linked notes, checked media and a
small optional unreviewed card batch. Save a checkpoint and a brief unanswered
check; keep later material locked. Give the learner the standard Study setup
link, account switcher, exact Modal authorization commands and source/app links.
Back up source/config/code separately from private learner data and credentials.
Report remaining owner actions or unavailable capabilities explicitly. An honest
partial readiness report is preferable to a claim of universal perfect output.


## Communicate owner steps when needed

Once running, use study_setup(topic=...) for accounts, Modal, books, cards, memory,
visuals or initial setup. Execute routine authorized technical work yourself.
Present only the immediate owner action and its reason, then verify it. The
learner does not need to read the complete setup manual before studying.
A medical learner uses the common infrastructure and an appropriate profile;
existing working integrations do not need reinstallation or fresh consent.
Keep separate learner installations/configurations and credentials. The added
local layer is not qualified for public shared multi-user hosting.
