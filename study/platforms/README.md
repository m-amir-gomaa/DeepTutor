# Platform setup for the agent

Default learner: nontechnical, one independently authorized Codex account,
no Modal, no API key, no assumed free credit. Do not make the learner provision
every service or operate a terminal before a first useful lesson. Read the
[agent contract](../SETUP-AGENT.md) and the matching platform guide:
[macOS / Apple Silicon](macos.md), [Linux](linux.md), [Windows](windows.md).

## Standard private layout

```text
~/DeepTutor/
  app/                       public fork checkout; .venv/ and web/ live here
  config/installation.json  private non-secret paths and feature settings
  runtime/                   native DeepTutor settings, authorization and chats
  library/
    medicine/                independent Obsidian/Markdown vault
    research/                independent vault, goals and progress
    .control/                registry, native tools, readiness and checkpoints
    .workspaces/             native app workspaces and served artifacts
  tools/mineru/
    venv/                    native parser environment, separate from the app
    home/                    MinerU config.yaml and models/
  logs/
  backups/
  SETUP-STATUS.md             agent-maintained steps and next owner action
  Start Study.command        macOS launcher; Start Study.sh on Linux
```

An existing checkout may stay elsewhere; the helper records its actual path.
Never relocate an existing learner or overwrite their configuration to match
an example. The public Git checkout contains no books, private settings, grants
or learner evidence. Back up library/config/runtime separately and privately;
copying the public repo alone does not back up the learner.

After the source Python dependencies are installed, run from the app environment:

```sh
python study/platform_setup.py inspect
python study/platform_setup.py init --root "$HOME/DeepTutor" --profile medicine --name Medicine --slug medicine
python study/platform_setup.py init --root "$HOME/DeepTutor" --profile research --name Research --slug research
```

Inspection reads machine metadata without models, downloads or provider calls.
Initialization creates private files, profiles and a launcher; it neither installs
dependencies nor claims readiness. Use the generated configuration and runtime
for every management command and backend process:

```sh
export DEEPTUTOR_STUDY_CONFIG="$HOME/DeepTutor/config/installation.json"
export DEEPTUTOR_HOME="$HOME/DeepTutor/runtime"
export DEEPTUTOR_STUDY_LAYER="$HOME/DeepTutor/app/study"
deeptutor init --non-interactive
# Start the app, then attach, using the same interpreter/environment:
deeptutor start --detach --no-browser
python study/manage.py attach
python study/manage.py doctor
```

If the checkout is elsewhere, use that actual study-layer path. Confirm app and
study origin ports match. `Start Study.command` starts the app before opening
the controls; `manage.py open` by itself only opens a browser. Check a real
stop/relaunch before handoff, not just launching from an activated terminal.

## Agent-managed human actions

Execute technical setup, tool discovery, configuration and verification. Pause
only for the immediate missing input or native sign-in/admin authorization that
the learner must supply. Explain one click/action and its purpose, confirm the
result, then continue. Do not expose tokens or ask for passwords in chat.

GitHub signup is unnecessary for public cloning. Offer it later for private
backup/contribution only if wanted. The host coding agent and DeepTutor each
authorize through their supported flow; use the learner's single account, never
copy another installation's credentials. Add alphaXiv only when useful and guide
its OAuth when requested. Start public literature lookup with relevant public
PubMed/bioRxiv/publisher resources; an absent optional service must not block
textbook teaching. Preserve the exact learner-selected model and spending policy.

Record setup in `SETUP-STATUS.md` and `.control/readiness.json`: component,
version, installed/configured/authorized/exercised, dated check, artifact, and
next action. Do not seed the author's successes or rate a flashcard for a learner.
Prepare original-source text/figures first; optional OCR, generated animations
and audio can become ready separately. Avoid enormous model downloads or running
MinerU and a rendering VM simultaneously on a low-memory Mac.

## Optional isolated teaching renderer

Linux keeps bubblewrap. On macOS, generated Python/Manim uses an explicitly
configured local Docker-compatible runtime, for example Colima. No cloud account
is required. After installing the runtime and reviewing the local build recipe:

```sh
docker build -t deeptutor-study-render:local study/render-image
docker image inspect --format '{{.Id}}' deeptutor-study-render:local
```

Save the returned immutable `sha256:...` ID under `execution.image`, set
`execution.backend` to `container` and `tools.container` to the actual client.
The lesson runner refuses an unpinned image, never pulls during a lesson, has
no network, runs as the learner's UID, and mounts only the output folder. It
limits memory, CPU, process count and file size. Test an example and a short
Manim render, network denial, output persistence and timeout cleanup. The
minimal image has no LaTeX installation: add/qualify TeX only if a lesson needs
it. Do not run generated code directly on the Mac to bypass a missing runner.
Original PDF figures and checked HTML teaching do not depend on this VM.

MinerU stays native on macOS to use Apple GPU support. The Linux rendering VM
is a separate capability; it does not provide CUDA on an Apple GPU.
