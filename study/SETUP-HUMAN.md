# Set up your study system

The fork adds a standard study layer to DeepTutor: source-aware studying,
discipline profiles, reusable prompts, chronological routes, Markdown/Obsidian
notes, Anki delivery, checked visual tools and optional Modal PDF processing.
Each learner supplies their own books and authorizes their own providers.

## Open the standard controls

Open DeepTutor, then the **Study setup** page:
`/api/settings/study/page` on the same address as your DeepTutor web app.
Bookmark this page. Its **Accounts & Modal** tab links to the account switcher,
shows Modal metadata and gives your installation's exact terminal commands.
The **Prompt templates** tab lets you choose a discipline, fill in a topic or
paper, edit the prompt and copy it. Open Chat and paste; copying never runs it.
You can also ask the tutor: “Open my study setup and account controls.”

## Fresh installation from the fork

The initial supported deployment target for the added local execution layer is
Linux. Native DeepTutor supports additional platforms; the bubblewrap-based
runner and native media tools need platform-specific substitutes there.

1. Follow the fork's upstream `docs-for-dev/AGENT_SETUP.md` to create a Python
   3.12 environment, install `requirements/full.txt`, install the checkout with
   `python -m pip install -e . --no-deps`, and install/build the web frontend.
   Use the fork's `study-standardization` branch, based on v1.7.1.
   Install the layer additions with `python -m pip install -r study/study-runtime-requirements.txt`.
2. Set a private runtime home outside the checkout. For example:
   `export DEEPTUTOR_HOME="$HOME/.local/share/deeptutor-study/runtime"`.
   Run `deeptutor init --non-interactive`. No model is authorized by this step.
3. Run `python study/manage.py init --profile medicine --name "Medical study"`.
   This prepares a separate study folder and non-secret configuration. Choose
   `general`, `college`, `algorithms`, `medicine`, `biology`, `research`,
   `maths-ml` or `coding`. Choose the discipline, goals, language and preferred
   depth for this learner; the included medical profile is a starting point.
4. Start `deeptutor start --no-browser` with the same runtime home. Run
   `python study/manage.py attach` to register the prepared vaults and their
   scoped study tools/skills through the local owner API. It preserves existing
   resources and reports missing optional integrations rather than inventing them.
5. Sign in to your chosen model in DeepTutor. For Codex, use native
   `deeptutor provider login openai-codex`. A second account is optional; its
   independent authorization lives on the account-control page. Choose a model
   your account actually supports; this fork does not buy model access.
6. Open Study setup. Put owned study PDFs into the new subject's `inbox/` and
   use the import template. Plan a small initial unit from the actual edition;
   do not hand an agent an entire library and infer it has checked every page.

The standard configuration has no user books, OAuth grants, API keys, medical
records, prior chats or achievements. Your installation stays separate from the
author's personal setup. `installation.json` and `installation.*.json` are local
configuration files and excluded from Git. Credentials stay in native stores.

## The daily workflow

Use **Start or resume a unit** or **Continue from my checkpoint**. The tutor
reads the route, actual source pages and preferences, teaches the current part,
creates useful visuals, saves notes and offers a small card batch. Give your own
answer to its check. Review Anki yourself; the tutor never assigns your rating.

Obsidian displays the same Markdown notes. Neovim can edit those files directly.
This is one private learner installation per runtime/configuration; the added layer has not been qualified as a shared multi-user teaching service.

The separate cards outbox prevents retries from creating duplicate notes. Anki
delivery needs the local authenticated Anki MCP service, the `Study Concept`
note type and the subject deck; read the integration checklist in the agent guide.
Until these are configured, cards remain visibly pending. Your reading, assisted
work, attempts and delayed checks remain separate forms of evidence.

Medicine and research use the same infrastructure. The medical profile connects
structure/function with mechanism and uses source figures for accurate anatomy.
The research profile asks for primary methods/results, dates, preprint status,
study design, effects and limitations. Use PubMed and bioRxiv when relevant.
Educational cases are fictional; do not import identifiable patient records.
Research summaries are not automatically systematic reviews or clinical advice.

## Codex account selection

From Study setup → **Accounts & Modal** → **Open account controls**. It shows
display names, this workspace's preference, the effective next account and the
account behind the latest completed model call. The current call cannot move
mid-stream. Subsequent calls observe the new setting. Automatic selection may
try the other authorized account before output begins; strict selection can
disable that fallback. Each account keeps its own allowance and reset time.

Prompts include **Identify my current account**, **Use the secondary account**
and **Restore automatic account selection**. If neither model can run, use the
page yourself; it needs the local backend, not a successful model call.

## Modal tokens and optional OCR

Local PDF extraction is the default. The optional private worker uses the same
MinerU 4.1.3 Standard output contract and uploads only the requested page subset.
Changing the OCR location does not reprocess cached corrected pages. The legacy
native upload adapter remains local; the setting belongs to `prepare_pdf`.

Use the commands displayed on Study setup → Accounts & Modal. The normal flow is
`python -m modal token new`: finish your own browser authorization. For a token
issued in the Modal dashboard, use `python -m modal token set --token-id -
--token-secret -` in your own terminal; the prompts hide the values. Then use
`python -m modal profile list` and `python -m modal profile activate PROFILE` to
choose a workspace. The actual page supplies your isolated interpreter path.
Never paste tokens into chat or commit them. After rotation, recheck the worker.

A fresh fork starts with cloud processing disabled and no assumed free credit.
Before enabling it, confirm your own current plan, credit, net spending limit,
reservation cap and desired workspace. Set only non-secret values under `modal`
in `installation.json`, then deploy `study/modal_mineru_app.py` using your Modal
SDK. Explicitly choose Modal in the vault only after the worker is verified.
The worker reserves conservatively before admitting a job. These reservations
are not exact bills or a separate account; metering can lag. No setup script
raises a budget or creates a paid-provider fallback automatically.

Authoritative token/profile references:
[Modal tokens](https://modal.com/docs/cli/latest/token),
[Modal profiles](https://modal.com/docs/cli/latest/profile),
[Modal configuration](https://modal.com/docs/sdk/py/latest/config).

## Understand readiness

Installed, configured, authorized and successfully exercised are separate states.
`python study/manage.py doctor` reports those it can observe. It never uploads a
book, invokes a model or spends cloud compute simply to report installed tools.
The agent guide specifies bounded live checks after your authorization. New
books and new generated media still need source and content checking.
