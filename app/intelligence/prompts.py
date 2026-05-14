from pydantic import BaseModel, Field
from typing import List

# --- RELEVANCE SCORING ---
SCORING_SYSTEM_PROMPT = """
You are a professional technical recruiter. Your task is to compare the provided candidate profile with the job description (JD) and return an analysis strictly in JSON format.

Analysis rules:  
1. Scoring (0-100): Based on technical skill match, years of experience, and location fit.  
2. Flags: Mark critical obstacles such as visa sponsorship required, German language mandatory, or "Senior" expectation.  
3. Decision: If 85+ 'auto_apply', between 60-85 'ask_user', below 60 'reject'.

Do not add any explanations or text outside of the JSON whatsoever.
"""

class RelevanceScoreOutput(BaseModel):
    score: int = Field(..., description="0-100 matching score")
    reasoning: List[str] = Field(..., description="Bullet points explaining the score")
    critical_flags: List[str] = Field(..., description="Critical obstacles like Visa, Language")
    decision: str = Field(..., description="One of: auto_apply, ask_user, reject")

# --- CV TAILORING ---
CV_TAILORING_PROMPT = """
Your task is to select and order the most suitable ones for the job posting from the candidate's raw dataset (Master Data).   
RULE: Do not generate new data, do not change existing sentences. Order using only the provided IDs.

Input:  
- Master_Skills: [ID, Name, Category]  
- Master_Projects: [ID, Title, Description, Tech_Stack]  
- Job_Description: [Text]

Output:  
Return a JSON object containing only the selected IDs.
"""

class CVTailoringOutput(BaseModel):
    tailored_summary: str = Field(..., description="Rewritten summary focusing on JD keywords")
    selected_project_ids: List[int] = Field(..., description="List of chosen project IDs")
    top_skill_ids: List[int] = Field(..., description="List of chosen skill IDs")
    keyword_injections: List[str] = Field(..., description="Keywords matched from JD")

# --- DOM VISION FALLBACK ---
DOM_VISION_PROMPT = """
Find the CSS selector for the '{field_label}' field on this form page.
ONLY return the selector string, do not write anything else.
Example output: input[name='salary_expectation']
"""

class DOMVisionOutput(BaseModel):
    selector: str = Field(..., description="The detected CSS selector")
