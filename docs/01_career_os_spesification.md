# **Personal Career Operating System (PCOS) Technical Specification**

## **1. Funnel Tracking Metrics (Funnel Analysis)**

To measure the efficiency of the system, each stage is tracked as a "conversion rate".

* **Scanned:** Total number of raw postings pulled from sources (LinkedIn, Indeed, etc.).  
  * *KPI:* Scraper efficiency and source quality.  
* **Matched:** Those that pass the LLM/Embedding filter and receive "applicable" approval.  
  * *KPI:* Filter precision (Precision/Recall). If too many irrelevant postings are matched, the prompt or embedding threshold is tightened.  
* **Applied:** Applications that pass manual approval or are auto-completed with a high confidence score.  
  * *KPI:* Execution speed.  
* **Interview:** Postings that received a response (Detected via email or LinkedIn message).  
  * *KPI:* Product-Market Fit. This is the most critical metric.

## **2. Adaptive Strategy Engine Logic**

The system queries the database at the end of each "session" and updates its filters.

### **Decision Matrix**

1. **Country Analysis:**  
   * If interview_rate("DE") > interview_rate("NL") * 1.5:  
   * Increase the scanning frequency of Germany postings by 50%,  
   * Increase the confidence_threshold for the Netherlands by +10.  
2. **Stack Analysis:**  
   * If the interview rate from postings containing "React Native" is higher than "Backend/FastAPI" postings: Instruct TailorAgent to move React Native projects to the top of the CV.  
3. **Timing:**  
   * Calculate which hours yield the most responses from submitted applications (Prime-Time Apply).

## **3. Automation Data Flows**

### **A. Rejection Analysis**

* **Input:** Emails received via Gmail/Outlook with keywords "Unfortunately" or "Decided to move forward".  
* **Process:** LLM reads the email and categorizes the reason for rejection:  
  * Skill Gap (Insufficient technical skill)  
  * Visa/Relocation (Visa issue)  
  * Seniority (Seniority mismatch)  
* **Output:** The "Missing Skills" list is updated on the Dashboard.

### **B. Interview Prep**

* **Input:** ResearchAgent is triggered when one of the following signals is detected:   
  * Calendar invite (ICS attachment or Google Calendar invite)   
  * Keywords in email: "interview", "screening", "quick chat", "let's connect", "call with", "meet with", "speak with", "next steps"   
  * LLM classification: Email text is sent to Groq with the question "is this an interview invite?", human approval is requested in ambiguous cases.   
* **Process:** ResearchAgent is triggered:  
  1. Scan the company's news from the last 6 months.  
  2. Analyze the LinkedIn profile of the interviewer.  
  3. Extract "5 likely technical questions" from the posting text.  
* **Output:** A "Prep-Doc" link is provided via the Web GUI and sent via Telegram.
