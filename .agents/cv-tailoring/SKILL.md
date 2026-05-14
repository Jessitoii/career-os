---
name: cv-tailoring
description: Use when implementing or modifying the CV tailoring pipeline — selecting the right CV version, reordering project/skill blocks for a specific job, generating dynamic cover letters, or updating the tailoring prompt contract. Triggers on: "CV seçimi", "CV tailoring", "özgeçmiş optimizasyonu", "cover letter", "immutable block selection", "CV versiyonu", "keyword injection", "tailored summary", "proje sıralama".
---

# CV Tailoring Skill

## Use this skill when
- Selecting the optimal CV version for a specific job listing
- Reordering skill/project blocks without fabricating new content
- Generating a dynamic cover letter or "brief" PDF
- Updating the tailoring prompt contract or JSON schema
- Debugging why the wrong CV version was selected

## Do not use this skill when
- General LLM prompt engineering unrelated to CV content
- Managing CV files on disk/S3 (that's infrastructure, not this skill)

## Core Principle: Immutable Block Selection
The agent NEVER generates false experience or skills. It only:
1. **Selects** which existing blocks to include (from Master Data)
2. **Reorders** blocks by relevance to the JD
3. **Rewrites only the Summary** (1-2 sentences, with JD keywords)

## Instructions

### Step 1: Select CV Version
```python
async def select_cv_version(job: JobListing, cv_docs: list[CVDocument]) -> CVDocument:
    """
    Use LLM to pick the best CV version from available options.
    cv_docs.metadata contains keywords extracted from each CV PDF.
    """
    prompt = f"""
    Job requires: {job.detected_stack}
    Available CV versions: {[{'id': cv.id, 'name': cv.version_name, 'keywords': cv.metadata['keywords']} for cv in cv_docs]}
    Return ONLY the id of the best matching CV version as JSON: {{"selected_cv_id": "..."}}
    """
    # Use call_with_fallback('cv_tailoring', prompt)
```

### Step 2: Tailor Block Order (Prompt Contract)
System prompt:
```
Görevin, adayın ham veri setinden iş ilanına en uygun olanları seçip sıralamak.
KURAL: Yeni veri üretme, var olan cümleleri değiştirme. Sadece ID'leri kullanarak sıralama yap.
```

Input payload:
```json
{
  "master_skills": [{"id": 10, "name": "FastAPI", "category": "backend"}, ...],
  "master_projects": [{"id": 1, "title": "OpenReef", "tech_stack": ["FastAPI", "LLM"]}, ...],
  "job_description": "..."
}
```

Output schema (validate with Pydantic):
```python
class TailoringOutput(BaseModel):
    tailored_summary: str = Field(max_length=300)
    selected_project_ids: list[int] = Field(min_items=1, max_items=5)
    top_skill_ids: list[int] = Field(min_items=3, max_items=10)
    keyword_injections: list[str] = Field(max_items=5)
```

### Step 3: Generate Cover Letter / Brief PDF
```python
# Use reportlab or fpdf2
from fpdf import FPDF

def generate_cover_letter(tailoring: TailoringOutput, job: JobListing, profile: UserProfile) -> str:
    pdf = FPDF()
    pdf.add_page()
    # ... populate with tailored_summary, selected projects, keyword_injections
    output_path = f"/storage/cover_letters/{job.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf.output(output_path)
    # Save path to applications.application_data['cover_letter_path']
    return output_path
```

### Step 4: Archive
After generation, update `applications` table:
```sql
UPDATE applications SET 
    cv_id = $1,
    application_data = application_data || '{"cover_letter_path": "$2", "tailored_keywords": $3}'
WHERE id = $4;
```

## Model
Use `claude-sonnet-4` as primary (quality matters for CV language).
Fallback: `gpt-4o-mini` → `groq/llama-3-70b` → `ollama/llama3:8b`
(See `rate-limit-fallback` skill for chain implementation)

## Performance Tracking
Query `cv_performance_stats` VIEW regularly to see which CV version has the highest `conversion_rate`. Switch default version if another outperforms by >5%.
