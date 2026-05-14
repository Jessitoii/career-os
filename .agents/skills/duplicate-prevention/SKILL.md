---
name: duplicate-prevention
description: Use when implementing or debugging the 3-layer duplicate application detection system — DB hash check, email parsing for manual applications, or semantic vector similarity detection. Triggers on: "duplicate prevention", "mükerrer başvuru", "aynı ilana iki kez", "email parsing", "Gmail API kontrolü", "semantic duplicate", "URL hash", "95% similarity", "already applied".
---

# Duplicate Prevention Skill

## Use this skill when
- Implementing any of the 3 duplicate detection layers
- Debugging a case where the same job was applied to twice
- Adding Gmail/Outlook email scanning for out-of-system applications
- Tuning the semantic similarity threshold

## Do not use this skill when
- General embedding work unrelated to duplicate detection (use `scoring-engine`)

## Three Layers (Run in Order — All Three)

### Layer 1: DB Hash Check (Instant, ~0ms)
**When**: Immediately at Discovery start, before any LLM calls.

```python
import hashlib

def make_job_hash(url: str = None, company: str = None, role: str = None) -> str:
    if url:
        return hashlib.sha256(url.encode()).hexdigest()
    # Fallback: company+role composite key
    key = f"{company.lower().strip()}::{role.lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()

async def is_duplicate_db(job: JobListing, db) -> bool:
    result = await db.fetchrow("""
        SELECT id FROM job_listings 
        WHERE external_id = $1 OR url = $2
        LIMIT 1
    """, job.external_id, job.url)
    return result is not None
```

### Layer 2: Email Parsing (Intelligence, catches out-of-system applications)
**When**: After Discovery, before Scoring.

```python
# Uses Gmail MCP or Gmail API
APPLIED_KEYWORDS = [
    "application received", "thank you for applying",
    "we received your application", "başvurunuz alındı",
    "your application has been submitted"
]

async def check_email_for_application(company: str, role: str) -> bool:
    """Search Gmail last 30 days for application confirmation from this company."""
    query = f"from:{company} ({' OR '.join(APPLIED_KEYWORDS)}) newer_than:30d"
    # Via Gmail MCP: search_threads(query=query)
    # If results found → log as manual entry, mark is_manual_entry=True
    threads = await gmail_search(query)
    return len(threads) > 0
```

### Layer 3: Semantic Detection (LLM/Vector, catches renamed/reposted jobs)
**When**: During Scoring phase, after embedding is generated.

```python
SEMANTIC_DUPLICATE_THRESHOLD = 0.95

async def is_semantic_duplicate(new_embedding: list[float], db) -> tuple[bool, UUID | None]:
    """Find any past application with >95% vector similarity."""
    result = await db.fetchrow("""
        SELECT jl.id, a.id as application_id,
               1 - (jl.embedding <-> $1::vector) as similarity
        FROM job_listings jl
        JOIN applications a ON a.job_id = jl.id
        WHERE 1 - (jl.embedding <-> $1::vector) >= $2
        ORDER BY similarity DESC
        LIMIT 1
    """, new_embedding, SEMANTIC_DUPLICATE_THRESHOLD)
    
    if result:
        return True, result['application_id']
    return False, None

# If semantic duplicate found:
# → Mark job as 'possible_duplicate'
# → Send to AWAITING_APPROVAL (never auto-apply)
# → Include similarity score and original application in Telegram message
```

## Instructions

### Full Duplicate Check Orchestrator
```python
async def run_duplicate_checks(job: JobListing, embedding: list[float], db, gmail) -> DuplicateCheckResult:
    # Layer 1
    if await is_duplicate_db(job, db):
        return DuplicateCheckResult(is_duplicate=True, layer=1, action='discard')
    
    # Layer 2
    if await check_email_for_application(job.company_name, job.title):
        await log_manual_entry(job, db)
        return DuplicateCheckResult(is_duplicate=True, layer=2, action='mark_manual')
    
    # Layer 3
    is_dup, orig_app_id = await is_semantic_duplicate(embedding, db)
    if is_dup:
        return DuplicateCheckResult(is_duplicate=True, layer=3, 
                                    action='ask_user', original_application_id=orig_app_id)
    
    return DuplicateCheckResult(is_duplicate=False)
```

## Safety
- Layer 1 and 2 checks must complete before any embedding API call (saves cost).
- Semantic duplicates must NEVER auto-apply — always escalate to human review.
- Log all duplicate detections in `interaction_logs` with `action_type='duplicate_detected'`.
