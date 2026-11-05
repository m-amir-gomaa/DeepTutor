# Linux setup

Follow the source install and [standard layout](README.md). Python 3.12 and
Node 22 are the baseline; prefer the distribution's packages or pinned project
environment. On NixOS read that machine's repository instructions and supply
its actual native-wheel library environment; never copy another user's paths.

Generated Python/Manim keeps bubblewrap isolation, with Manim/NumPy and their
native libraries available inside the read-only binds. Install native FFmpeg,
Pango/Cairo and fonts as needed. Draw.io's headless export uses Xvfb on Linux.
Configure actual executable paths and verify renders; do not mark them ready
from `which` alone. The optional container route is also available explicitly.

For local MinerU, use a separate Python 3.12 environment and the actual hardware's
supported backend. The provided default is CPU/ONNX/llama.cpp on non-Apple hosts;
the setup agent can deliberately select/qualify an appropriate accelerator
configuration. Download and verify models during setup, then parse offline.
No Modal or second Codex account is required.

Existing installations retain their own library/runtime/configuration and
explicit parser wrapper. Do not reinitialize them into the example folder or
replace their selected model, kernel, driver or budget as incidental setup.
