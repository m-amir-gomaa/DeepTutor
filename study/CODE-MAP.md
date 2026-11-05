# Where the code and learner data live

The fork has one reusable study layer. Discipline profiles choose goals and
relevant services; they do not create separate implementations for medicine,
algorithms or any other subject.

```text
DeepTutor/                         Version-controlled application source
├── deeptutor/                     Upstream Python app plus targeted fixes
│   ├── services/study_bridge.py   Loads study/ without copying learner data
│   ├── services/codex_auth/       Native owner OAuth storage and sign-in
│   ├── services/mcp/             Native tools/OAuth transport
│   └── api/routers/settings.py   Owner-only setup/account routes
├── web/                          Upstream React/Next.js interface
│   ├── components/sidebar/       Workspace menu → Study setup
│   └── ...                      Source fixes for OAuth/research/audio UI
└── study/                        Shared additions
    ├── manage.py                 Initialize, attach, inspect, open
    ├── platform_setup.py         Private first-run layout and Finder launcher
    ├── platforms/                Agent/human OS-specific setup contracts
    ├── mineru_local.py           Offline native Apple/CPU parser selection
    ├── execution.py              Linux/optional local-container isolation
    ├── render-image/             Explicit local teaching image build recipe
    ├── study_settings.py         Non-secret per-installation configuration
    ├── discipline_profiles.json  Shared goals/teaching/service preferences
    ├── prompt_catalog.json       Reusable editable prompt templates
    ├── setup_center.*            Setup page and human-help responses
    ├── study_tools.py            Scoped tools available to the tutor
    ├── library.py                Import, hashes, registries and FTS search
    ├── curriculum.py             First unit, chronological locks/advancement
    ├── progress.py               Notes, checkpoints and actual evidence
    ├── cards.py                  Duplicate-resistant Anki delivery outbox
    ├── source_pipeline.py        Shared local/Modal preparation contract
    ├── modal_*                   Private optional worker/client/admission
    ├── lesson_assets.py          Editable diagrams and native export checks
    ├── mode_bridge.py            Native-mode source/validation integration
    ├── codex_pool.py             Account selection and actual-use reporting
    ├── skills/                   Shared teaching/app/visual instructions
    └── test_*.py                 Temporary fixtures and regression checks
```

Outside Git, each installation has a private configuration and runtime home:

```text
private study folder/
├── medicine/                     Markdown/Obsidian vault
│   ├── inbox/                    New owned PDFs
│   ├── references/               Verified immutable managed copies
│   ├── sources/                  Prepared physical pages and extracted assets
│   ├── concepts/, reviews/, ...  Useful learner notes
│   └── .study/                   Course route, progress DB, local outboxes
├── research/                     Another independently scoped vault
├── .workspaces/                  Native app content for new installations
└── .control/                     Registries, FTS index and private receipts

private DeepTutor runtime home/   Native settings, chat history and app runtime
native provider stores/           Authorization; never committed or copied
```

Existing installations can map a vault to a different native content directory.
`manage.py attach` must preserve its stored workspace ID; path equality is not
proof of identity. New installations keep their native app content separate from
the notes vault. Each learner uses their own runtime/configuration and accounts.

The installed Python package/compiled frontend are running copies of application
code. They are distinct from the Git checkout and from learner data. A source
installation loads the fork directly. A pinned existing installation can load
`study/` through `DEEPTUTOR_STUDY_LAYER`, with its private configuration selected
by `DEEPTUTOR_STUDY_CONFIG`. Keep matching core fixes; do not blindly patch or
upgrade an existing runtime.

The setup UI is a small addition, not a replacement interface. It centralizes
templates, account controls, Modal instructions and guides. The tutor's
`study_setup(topic=...)` supplies the same human instructions on demand, so a
learner normally stays in the chat. Runtime operation still belongs to DeepTutor.

## Typical flow

1. `manage.py init` prepares a profile and folders without authorizing providers.
2. `manage.py attach` registers the existing/new workspace, shared skills and its
   scoped study service while retaining existing resources.
3. DeepTutor's model calls `orientation`, which imports/indexes the subject inbox.
4. The tutor reads actual current-unit pages, prepares extraction when needed,
   teaches and invokes the selected visual/note/card tools.
5. Actual learner input can become evidence; generated lessons cannot.
6. Operational questions use `study_setup(topic=...)`; owner sign-in and reviews
   remain human actions, explained at the moment they are required.
