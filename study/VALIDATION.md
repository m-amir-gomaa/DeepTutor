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
