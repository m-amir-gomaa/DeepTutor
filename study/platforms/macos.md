# macOS and M3 MacBook setup: agent instructions

Use native arm64 tools and Python 3.12 on Apple Silicon. Detect `platform.machine()`,
`sysctl -n hw.memsize`, free disk space and existing tools before installing.
Do not assume an M3 MacBook has 16 GB RAM. Avoid Rosetta/x86 Python mixed with
arm64 packages. Preserve another Python environment or existing Homebrew setup.

The human starts via [OpenAI's official desktop guide](https://developers.openai.com/codex/app/)
and gives Codex [START-HERE.md](../../START-HERE.md). One account is sufficient.
Do not make them install Linux tools, use Neovim or change their default browser.
For Xcode Command Line Tools/Homebrew, follow the current official installers;
the agent handles commands and the human handles any native macOS permission.
Do not execute an unreviewed downloaded shell script.

## App and study setup

Clone the **fork** at `study-standardization` into `~/DeepTutor/app`, not the
upstream `dev` example. Install Python 3.12 and Node 22 using existing tools or
the current [Homebrew documentation](https://docs.brew.sh/Installation).
Create `app/.venv`; install `requirements/full.txt`, editable source with
`--no-deps`, and `study/study-runtime-requirements.txt`. Do not replace this
checkout with separately installed feature wheels. Build `web/` using its
lockfile (`npm ci --legacy-peer-deps`, then `npm run build`). Run `npm ci` in
`study/` and install Playwright Chromium for artifact validation.

Use the [standard layout commands](README.md), initialize medicine/research
profiles, start and attach through the native owner API. Ask the learner to
authorize their single provider through DeepTutor's native login. Verify one
bounded real answer and one owned-source lesson. Use her own browser/editor.
The launcher includes Homebrew's Node 22 paths because Finder does not load an
interactive shell environment. Check it from Finder after the app is stopped.

Install Obsidian/Anki/draw.io/Inkscape only where relevant using the official
app or package source. Keep each Obsidian vault separate. Configure the local
authenticated Anki service and its note type/deck; cards wait in the outbox
until actual delivery works. Preserve native FSRS settings. Draw.io uses the
macOS app executable and a temporary export profile; **do not install Xvfb**.
Source figures use PyMuPDF and require neither Draw.io nor an image API.

## Local MinerU on her Apple GPU

Use the native `tools/mineru/venv` with Python 3.12 and **MinerU 4.1.3**. Set
`tools.mineru-kit` in private installation.json to that environment's executable,
and use the included `study/bin/mineru-local` wrapper. Set `mineru_home` and
`mineru_models` to the matching standard layout. Keep `local_pdf.device=auto`.

Set `MINERU_HOME` to that private home for setup operations. First run
`mineru-kit hardware info --json`; this is the no-download diagnostic. Check
native Torch/MPS availability and llama.cpp/Metal, not `nvidia-smi`. Native
Apple Silicon auto uses Torch/MPS with llama.cpp/Metal; it is not the author's
forced ONNX/CPU setup. Standard OCR should be qualified on the actual machine.
The upstream guidance recommends at least 16 GB unified memory for this route.

Before model download, explain expected disk/RAM requirements and use her
authorized local installation scope. Configure `model.base_dir` if changing
the model directory, then run the official setup commands in that environment:

```sh
mineru-kit models download --tier standard --source huggingface
mineru-kit models verify --tier standard
```

Downloads happen during setup. The study wrapper then uses local/offline mode,
rejects remote/config overrides and checks for remote VLM configuration. Its
readiness check asks MinerU to verify the actual backend's models; it does not
look for Linux-only ONNX filenames on a Mac. Confirm a one-page synthetic scan
through `prepare_pdf`, ZIP/provenance, cache and original-figure lookup, then
one page from the learner's book. Do not infer OCR quality from model presence.

With insufficient memory, explain which local quality tier is feasible. Normal
digital-text and original-figure study remain usable. The shared study OCR route
requests Standard and fails visibly if unavailable; it does **not** silently
downgrade to Basic or upload. Offer a deliberate adapter/tier change with its
quality tradeoff, or the optional Modal route only if she wants it. She does
not need a Modal account to begin, and setup must not create cloud charges.

References checked 2026-11-05: [MinerU installation](https://opendatalab.github.io/MinerU/quick_start/),
[platform/backends and resource guidance](https://opendatalab.github.io/MinerU/usage/tiers/),
[models and offline mode](https://opendatalab.github.io/MinerU/usage/model_source/).

## Animation and example isolation

Use the optional container runner in the platform README. [Colima](https://colima.run/docs/installation/)
supports local Apple Silicon Docker workloads (`brew install colima docker`,
`colima start`). No second model account or container-cloud subscription is
needed. Build the image locally; record its immutable ID and qualify it before
marking animations ready. Stop the VM when it is not needed. Do not run a large
OCR job alongside it on a memory-constrained machine. Native GPU OCR and the
Linux VM renderer have separate tests.

No physical M3 or learner account is exercised merely by reading this guide or
passing portable CI. The setup agent records her own actual acceptance.
