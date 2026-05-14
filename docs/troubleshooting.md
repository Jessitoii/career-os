# Troubleshooting Guide

During initial execution verification, the following issues were surfaced. If you encounter them on the target machine, use these verified fixes.

## 1. Out of Memory (OOM) Errors during npm install
**Symptoms:**
- `npm install` hangs or terminates silently.
- PowerShell or terminal crashes with `Starting the CLR failed with HRESULT 80004005.`
- Python commands crash with `[ERROR] Failed to launch python.exe (0x80070008)`.

**Root Cause:**
Next.js dependencies (specifically native SWC binaries like `@next/swc-win32-x64`) consume significant memory during resolution/extraction. This occurs on RAM-constrained machines.

**Actionable Fix:**
- Execute this on the main development PC with sufficient memory (8GB+ free RAM).
- Avoid running `docker-compose up` concurrently with heavy `npm install` processes if memory is tight.

## 2. PostgreSQL Connection Hanging
**Symptoms:**
- `pytest tests/test_db_connection.py` takes 30+ seconds to skip or fail.

**Root Cause:**
SQLAlchemy's `create_engine` defaults to the OS TCP timeout if the port is reachable but dropping packets.

**Actionable Fix (Already applied):**
The codebase now includes `connect_args={'connect_timeout': 3}` in `app/core/db.py` to ensure fast-failing.

## 3. Rate Limits (LLM Providers)
**Symptoms:**
- `call_with_fallback` warns about `per_minute` or `per_day` limits.

**Root Cause:**
Groq and Cerebras have strict rate limits on free/developer tiers.

**Actionable Fix (Already applied):**
The LLM client dynamically reads the `retry-after` header and pauses execution, then seamlessly falls back to the next model in `MODEL_CHAINS` (e.g. `llama-3-70b-8192` -> `mixtral-8x7b-32768`). No intervention is required.
