# Verification of this implementation

## Portable first-run and macOS additions, 2026-11-05

The current local portable suite passes **102 tests**, including 13 platform/layout,
Mac Draw.io routing, local-only MinerU, generated-code isolation/cleanup and
real synthetic PDF import/hash/bookmark/render/search/subject-isolation checks.
These fixtures preserve learner edits, single-account defaults and disabled
cloud processing. Fresh default backend origin matches upstream port 8001;
explicit existing installation URLs are preserved.

Hosted acceptance [run 42025735828](https://github.com/m-amir-gomaa/DeepTutor/actions/runs/42025735828)
passed at code commit `51fffde2` on 2026-11-05: **all three jobs succeeded**.
The full Linux suite passed all 102 tests; native macOS ARM64 passed the 13
platform/PDF fixtures; the real local container built and passed Python output,
network/read-only-root restrictions, Manim MP4 and timeout/cleanup checks.
No model account, cloud compute or private learner material was used by CI.

The M3 setup contract, nontechnical Start Here, private layout and Finder launcher
are versioned. CI separately checks Apple Silicon setup and a locally built
container image's actual Python/network/write limits/Manim output/timeout path.
Record the CI result separately from the local suite. Physical M3 GPU OCR,
native app integration and the new learner's authorization remain her setup
agent's checks; a mocked platform test or hosted runner does not establish them.

The author's existing Linux installation retains its explicit local parser,
bubblewrap route, accounts, budgets and personal library. No new model call,
model download, cloud deployment or learner progress followed from these changes.

## Earlier implementation acceptance

The first hosted run at `4d9e37ca` passed the macOS ARM64 setup/PDF fixtures
and the actual Linux container's Python/network/write restrictions, Manim MP4
and timeout path. Its full Linux suite caught a browser-driver issue: tests
and mode validation auto-discovered a system Chromium wrapper instead of using
the Playwright-managed browser. The browser process crashed in a sandboxed
srcdoc frame. The follow-up uses the managed browser by default and preserves
intentional native overrides; sandbox/content/interaction checks remain enabled.
The local follow-up passed all 102 checks with the intentional NixOS native
browser override. NixOS environments with a separately packaged browser require their explicit
configured executable; an incompatible/missing managed browser fails visibly.

The portable study layer was developed against upstream DeepTutor **v1.7.1**.
Its source was started with a separate synthetic learner runtime. A medical
vault and a research vault were created and attached through the native API.
An original synthetic PDF passed intake, source hashing, bookmark inspection,
initial-unit planning, page reading, repeated import and cross-vault isolation.
Future pages stayed locked and no learner evidence was invented.

The production frontend built successfully. Its actual workspace menu opened the
Study setup page in the isolated medical workspace. Separate browser checks
exercised template selection, medical topic fields, literal untrusted text,
clipboard copying, Markdown download, workspace-bound account links and both
setup guides at 1440/1920 desktop widths.

On 2026-11-05 the portable suite passed **89 tests**, including text-only opening
lessons, optional interactive companions, and original PDF figure crops with
source hashes, workspace isolation and locked-page/invalid-region rejection.
The earlier core verification passed **147 relevant upstream tests**. Frontend
typechecking and **1,337 frontend logic tests** passed, including OAuth popup
ordering and failure handling. A rendered React
test verifies that Research confirmation stays disabled during the active turn.

The existing author's separately authorized installation also completed a real
agent turn using topic-specific setup help, and the private Modal worker parsed
an original scanned fixture after the portable packaging repair. Private
credentials, books, chat records and detailed operator receipts are excluded.

These are implementation checks, not a fresh user's readiness. The new learner
must authorize their own model/services and qualify the renderers, Anki delivery,
native modes and optional cloud route they actually choose to use. Clinical
correctness of future generated medical explanations is not certified by these
software tests. The included agent guide requires source/evidence checking.
# 7 November 2026 — temporary account extension

The scoped account suite passes 17 tests; the complete portable study suite passes
106 tests. New checks cover explicit workspace-only temporary selection, disabled
fallback, saved-account preservation, restoration on disconnect and refusal to
disconnect active inference. Existing two-account behavior remains exercised.

The actual local account page loads. A separate browser fixture exercises third
slot visibility, explicit selection, disabled fallback and disconnect restoration
with zero runtime errors. Full-page desktop captures at 1280 and 1920 widths were
reviewed independently: **ship** for this ordinary control-page extension. These
connected-state captures use fictional identities and do not prove OAuth or quota.

An owner-assisted fresh native authorization and an actual selected-model request
were separately observed locally. Private identities, grants, learner books and
turn logs are excluded from this repository. No claim of universal future provider
availability or all-mode requalification follows from this account change.

## Shared browser routing and trace readability, 7 November 2026

The portable suite passes **107 tests** after a real insertion-trace call exposed
a missing configured-browser environment in that tool's execution gate. Both the
general HTML validator and insertion tool now use the same browser configuration;
the managed Playwright default remains unchanged. A regression exercises the
actual scoped MCP tool and checks propagation of explicit browser/module paths.

The trusted insertion-sort renderer now shows the held key, logical gap,
zero-based indices and step counter, replaces sentences without glyph morphing,
and holds readable states in a 720p render. A local 20-state example completed a
real browser control/keyboard check and a 1280×720, 27.2-second Manim render;
representative initial, middle and final frames were inspected. These checks
qualify that artifact and the affected routing, not arbitrary future teaching
content or all optional modes. No private book material or provider grant is
included in source.

Hosted [run 42350966619](https://github.com/m-amir-gomaa/DeepTutor/actions/runs/42350966619)
passed at code commit `1718c233`: all **107 portable tests**, the macOS ARM64
setup/PDF fixtures and the actual isolated-container renderer checks succeeded.
Those container checks cover output, network/read-only-root limits, Manim video
and timeout cleanup. They do not establish physical M3 GPU OCR or a fresh
learner's native app/service authorization.

## Optional Kaggle batch route — 9 November 2026

The portable study suite passed 115 tests, including confirmed-failure retry,
workspace/provider isolation, pending extraction preservation and result hashes.
The native Chromium runtime was supplied explicitly for the browser checks.
Actual local Study setup at desktop widths 1024/1440 exercised provider changes,
reload persistence, live quota reading and the loaded Modal authorization controls.
The scoped MCP exposed the new jobs tool and read the selected provider without
inference. The real provider test used one original synthetic PDF page: MinerU
4.1.3 Standard, two Tesla T4 GPUs, 97.2 seconds, verified input/output hashes,
shared page/ZIP/Markdown/FTS handling, cache reuse and notebook cleanup.
No user book, learning evidence or commercial source was used. This is not a
whole-book fidelity benchmark. One account and personal study only; see
GPU-PROVIDERS.md. Each new installation still needs its own authorization and
bounded live qualification.
