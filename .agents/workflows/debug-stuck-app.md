---
description: Diagnose and recover a stuck application.
---

## Diagnostic Steps

### 1. Query Current Status
```sql
SELECT
    a.id,
    a.status,
    a.last_status_change,
    NOW() - a.last_status_change           AS stuck_duration,
    a.application_data,
    jl.title,
    jl.company_name,
    jl.source
FROM applications a
JOIN job_listings jl ON a.job_id = jl.id
WHERE a.id = '<application_id>';
```

### 2. Fetch the Last 10 Interaction Logs
```sql
SELECT actor, action_type, content, payload, created_at
FROM interaction_logs
WHERE application_id = '<application_id>'
ORDER BY created_at DESC
LIMIT 10;
```

### 3. Intervene Based on Status

#### `pending_approval` and > 30 minutes elapsed
```sql
-- Manually trigger the timeout.py function
UPDATE applications
SET status = 'pending_later', last_status_change = NOW()
WHERE id = '<application_id>';

INSERT INTO interaction_logs (application_id, actor, action_type, content)
VALUES ('<application_id>', 'system', 'debug_intervention', 'Manual timeout: 30mins elapsed, set to pending_later');
```
Notify via Telegram: `"⏭ Manual timeout applied: <application_id>"`

#### `applying` and > 10 minutes elapsed
1. Find the last snapshot path from `interaction_logs`:
   ```sql
   SELECT payload->>'snapshot_path' FROM interaction_logs
   WHERE application_id = '<application_id>'
   ORDER BY created_at DESC LIMIT 1;
   ```
2. Examine the snapshot — where did the form get stuck?
3. Mark the application as `failed`:
   ```sql
   UPDATE applications SET status = 'failed', last_status_change = NOW()
   WHERE id = '<application_id>';
   ```
4. Notify via Telegram.

#### In `scored` status, has not transitioned to DECISION
```sql
SELECT relevance_score, application_data FROM applications
WHERE id = '<application_id>';
```
- Manually apply the `route_by_confidence()` logic based on the `relevance_score` value
- `score >= 85` → set to `approved`, trigger `apply_task.delay()`
- `60 <= score < 85` → set to `pending_approval`, send to Telegram
- `score < 60` → set to `rejected`

#### `pending_later` → Re-Queue
```sql
UPDATE applications SET status = 'approved', last_status_change = NOW()
WHERE id = '<application_id>';
```
```python
apply_task.delay('<application_id>')
```

### 4. Log the Intervention
```sql
INSERT INTO interaction_logs (application_id, actor, action_type, content, payload)
VALUES (
    '<application_id>',
    'system',
    'debug_intervention',
    'Manual debug intervention',
    '{"previous_status": "...", "new_status": "...", "reason": "..."}'::jsonb
);
```

## Expected Output
- Terminal: Diagnostic report
- DB: Status update + interaction log entry
- Telegram: Notification (if necessary)

## Related Skill
`session-lifecycle`, `hitl-telegram`
