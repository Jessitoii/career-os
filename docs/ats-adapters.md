# ATS Adapters Architecture

Career OS implements highly resilient adapters for parsing and submitting to Greenhouse, Lever, and Workday.

## The Execution Layer
The `ATSAdapter` base class (`app/automation/adapters/base.py`) enforces the following global rules:
1. **Human/Blocker Detection:** `safe_fill` and `safe_submit` preemptively check for CAPTCHAs, Cloudflare walls, or unexpected loops. If detected, the `requires_human` exception is thrown, halting execution and notifying Telegram.
2. **Dry Run Mode:** When `DRY_RUN=True` in `.env`, the adapter executes the entire flow, uploads resumes, and answers questions, but takes a snapshot and stops right before executing the final physical click.
3. **Trace Preservation:** Every execution natively records a Playwright trace `.zip` file capturing the exact DOM state, network payload, and visual screen context.

## Resume Selection Strategy
Adapters pull from the dynamic resume strategy implemented in `app/automation/resume.py`:
1. `optimized`: Job-specific CV pulled from the Document DB.
2. `generated`: Cached role-family CV (e.g., `Backend_Developer_cv.pdf`).
3. `master`: Standard master resume.
4. `fallback`: The emergency minimal PDF guaranteed to pass primitive parsers.

If all fail, the task is marked as `failed_apply` and dead-lettered for human review.
