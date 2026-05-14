# Debugging and Observability

Career OS incorporates deep observability to ensure automation failures are transparent and fixable.

## Global Kill Switch
If Playwright spirals or an ATS updates their UI causing recursive failure, you can freeze the system instantly:
- **Telegram:** Send `/pause`.
- **API:** POST `/system/pause` (Wired to the frontend emergency stop).

When active, Celery tasks acknowledge their queue item but use exponential backoff (`self.retry(countdown=300)`) instead of executing. The system goes dormant. Send `/resume` to thaw.

## Playwright Visibility (Headed Mode)
To visually watch the bots during local testing:
1. Open `.env`
2. Set `PLAYWRIGHT_HEADLESS=False`
3. Set `PLAYWRIGHT_SLOW_MO=500` (Simulates 500ms delay between actions to make them human-readable).

## Trace Extraction
When an application fails, the State Machine logs the `browser_trace_path` in PostgreSQL. 
To replay the exact execution:
```bash
playwright show-trace storage/traces/trace_<APP_ID>_error.zip
```
This opens a time-travel debugger showing DOM changes, clicks, and console logs.
