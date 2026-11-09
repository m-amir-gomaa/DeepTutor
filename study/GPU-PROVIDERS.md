# Choose where a study page is processed

Open the workspace menu → **Study setup** → **Accounts & processing**.
Choose Local, Kaggle or Modal and press **Use this provider**. This saves only
that workspace's OCR/layout preference; it does not start processing or change
the model, Codex account, other workspaces or public application budgets.
Digital text and unchanged verified extraction are reused locally.

## Personal study on Kaggle

Kaggle is optional and disabled in a new installation. Install the official
Kaggle CLI, then authorize **your own single account** with `kaggle auth login`
in the owner terminal. Finish any provider verification yourself. Never paste
tokens into a chat or configuration file. The setup agent adds only non-secret
settings to the existing private `installation.json`, preserving other keys:

```json
{
  "kaggle": {"enabled": true, "username": "YOUR_USERNAME", "max_seconds": 1800},
  "tools": {"kaggle": "/absolute/path/to/kaggle"}
}
```

Use the selector and **Check Kaggle quota**. The page distinguishes a configured
username from an unchecked connection. A quota read starts no compute job.
The agent should verify that native authorization belongs to the configured
username; a successful quota read alone does not establish that identity.

For an unlocked page, `prepare_pdf(..., backend="kaggle")` submits a private GPU
notebook. Its first result is normally **pending**. Call the same source/page
again later to check and collect; do not submit duplicates. The shared pipeline
checks hashes and the bounded MinerU ZIP, retains page images/layout, writes
Markdown/provenance and updates local physical-page search. Existing source
files and usable extraction survive provider failures. No silent Modal fallback
exists. Native general PDF uploads retain their existing local adapter.

Each job uploads one unlocked PDF page up to 2 MB, privately embedded in the
notebook code, with no public dataset. The job is capped at 5–30 minutes; model
download/install time counts. Available hardware, queue time and quota vary.
The output receipt names actual hardware; GPU allocation does not prove every
parser stage used CUDA or that formulas/tables were extracted correctly.

Use `kaggle_processing_jobs` to list/check jobs. A confirmed failed latest job
can be retried **only when explicitly requested**, with source and curriculum
access checked again. Unknown submissions must be inspected first. To stop a
running session, use its Kaggle notebook dashboard. Deleting a notebook is not
a guarantee of immediate cancellation or provider backup erasure. After a
successful collection the adapter removes its own temporary private notebook;
a cleanup failure stays visible and can be retried with the delete action.

[Kaggle terms](https://www.kaggle.com/terms) currently limit accounts to one
active account per person and services to personal non-commercial use. Do not
use account rotation or route client work, startup development or production
through this study adapter. Seek written permission for an exception. No
detection probability or private enforcement mechanism is assumed.

## Modal and local processing

Local remains the portable default. Modal is a separately authorized private
worker with the same result contract and conservative owner-defined spending
reservations. Choosing it is explicit. See SETUP-HUMAN.md for native token
commands and SETUP-AGENT.md for deployment/verification. Neither provider can
make an unreviewed scan perfectly accurate; inspect the original figures,
formulas and tables and preserve source-linked corrections.

## Commercial development and training

For a language-learning product, first test existing commercially licensed
models/APIs on representative tasks: scoring, correction, retrieval, speech
recognition and pronunciation are different evaluations. Fine-tuning is an
option after a repeatable measured gap, suitable data rights and a baseline;
training a foundation model from scratch is not a normal prerequisite.

- [Hugging Face Jobs](https://huggingface.co/docs/hub/jobs-training) runs training
  and fine-tuning scripts remotely, with explicit hardware/time limits and
  checkpoint/output storage. Useful for Transformers/TRL experiments.
- [Modal training examples](https://modal.com/docs/examples?category=training)
  provide programmable batch compute and fine-tuning workflows. Reuse existing
  deployment knowledge, but estimate GPU time and cap spending independently.
- [Runpod Pods](https://docs.runpod.io/pods/overview) offers GPU machines for
  custom environments; manage persistence, checkpointing and shutdown explicitly.

These are alternatives to evaluate, not provisioned accounts or fixed-price
recommendations. Check current rates, model/data licences and provider terms
before a commercial run. This fork launches none of them automatically.

## Qualification boundary

On 9 November 2026, the author exercised one original synthetic page with MinerU
4.1.3 Standard on two Tesla T4 GPUs. Processing took 97.2 seconds; input/output
hashes, one-page layout/Markdown and private-notebook cleanup passed. No learner
books or commercial material were uploaded for this check. This is evidence of
the basic route, not an accuracy benchmark or another installation's readiness.
