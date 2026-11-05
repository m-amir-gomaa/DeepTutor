# Standard study layer

Start with [the human guide](SETUP-HUMAN.md) or give [the agent guide](SETUP-AGENT.md)
to your setup assistant. This branch extends upstream DeepTutor v1.7.1.
The [code map](CODE-MAP.md) explains the directories and data flow; the
[validation record](VALIDATION.md) distinguishes tested implementation from a
new learner's own setup.

The same source-aware workflow supports college, algorithms, medicine, biology,
research, maths/ML and coding. Choose a profile; the fork supplies no personal
library, accounts or accomplishments.

Textbook lessons can use the original source figures directly: inspect the full
page with `source_page`, then publish a readable, unaltered crop with
`source_figure`. Crops retain the PDF hash, physical page and region; include
relevant legends, units and captions. Follow the learner's media preferences.
An opening lesson can be text-only; interactivity, audio and animation are optional.
The tutor can also build original plots, simulations, mechanism diagrams and
animations when they clarify structure or reasoning beyond the source figure.
The visual skill requires source comparison, calculation and render/interaction
checks; decorative text slides are not a substitute for an explanatory visual.

## Quick start after the upstream source install

```bash
export DEEPTUTOR_HOME="$HOME/.local/share/deeptutor-study/runtime"
deeptutor init --non-interactive
python study/manage.py init --profile medicine --name "Medical study"
deeptutor start --no-browser
# In another terminal with the same environment:
python study/manage.py attach
python study/manage.py doctor
python study/manage.py open
```

Open the workspace menu → **Study setup**. The page has editable/copyable prompt
templates, account controls, native Modal authorization commands and both setup
guides. Copying a template never executes it.

The management commands do not authorize models, spend cloud credit or rate
cards. Connect a model through DeepTutor, add owned PDFs to the subject inbox
and use the import/start templates.

## Configuration

`installation.json` is private non-secret configuration, generated locally and
ignored by Git. Override its location with `DEEPTUTOR_STUDY_CONFIG`; do not put
credentials in it. It owns library roots, loopback origins, executable locations
and optional cloud metadata. The default library is `~/DeepTutorStudy`, outside
the checkout. Use one configuration and runtime home per learner installation.

For browser validation, run `npm ci` in `study/` and
`npx playwright install chromium`. For Manim/code execution, install its
dependencies and bubblewrap on Linux. The isolated runner refuses host fallback.
Draw.io/Inkscape/FFmpeg and an authenticated Anki MCP service are optional,
independently verified integrations. Follow the guides rather than treating
presence as acceptance.

## Local and Modal OCR

Local remains default. Install MinerU 4.1.3 into an isolated environment, download
the Standard ONNX/llama.cpp models using its official commands, and configure
the reviewed local wrapper and model directory. `bin/mineru-local` uses the
configured `STUDY_MINERU_CLI` executable or `mineru-kit` on PATH. Run its model
download explicitly before offline parsing. No automatic cloud fallback exists.

Modal is disabled by default and assumes no free credit. Configure the
owner-approved policy, native authorization and app/profile, deploy
`modal_mineru_app.py`, check the private worker, then opt in from the tutor. Both
locations share validated ZIP/page provenance, local indexing and cache handling.
The legacy native upload adapter stays local. Credentials never pass through
prompt templates or setup-page forms.

## Tests and scope

```bash
PYTHONPATH=study:. python -m unittest discover -s study -p 'test_*.py'
```

Portable tests use temporary libraries and fake accounts. They do not authorize
or exercise your actual integrations. Record live provider/browser/renderer
checks privately in your own library. The author's personal acceptance is not
a fresh user's readiness.

Core fixes are integrated into source; no absolute-path patching of
site-packages is needed here. Optional third-party app harness fixes from the
author's machine are not vendored and require version-specific acceptance.
No books, business registries, credentials, chats or learner progress are bundled.
