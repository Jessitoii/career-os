# **Job Application Agent: Operational Execution Lifecycle**

This document defines the agent's daily execution cycle, state management, and human-agent interaction protocol.

## **1. Session Lifecycle (State Transitions)**

When the agent is started in the morning, it creates a SESSION_START event and proceeds through the following state machine until it shuts down.

### **State Flowchart**

1. **IDLE**: System is ready, waiting for commands.  
2. **DISCOVERY**: Pulling raw data from LinkedIn/Indeed/RSS sources.  
3. **FILTERING**: Duplicate prevention and "Auto-Reject" rules are running.  
4. **SCORING**: LLM and Embedding-based suitability analysis.  
5. **DECISION**:  
   * Confidence > 0.90: -> **EXECUTION** (Auto)  
   * 0.70 < Confidence < 0.90: -> **AWAITING_APPROVAL** (Web GUI & Telegram)  
   * Confidence < 0.70: -> **DISCARDED**  
6. **SUSPENDED**: Waiting for an answer from the user via GUI or Telegram (Async Pause).  
7. **EXECUTION**: Browser automation (Playwright) is filling out the form.  
8. **LOGGING**: Application result is recorded to DB, PDFs are stored.  
9. **COOLDOWN**: Random wait time for anti-bot protection.  
10. **SESSION_END**: Daily summary and shutdown.

## **2. Workflow Orchestration & Async Approval (GUI & Telegram)**

The system's ability to not "stay open constantly" and "ask questions" is managed via a **State Machine**.

### **Async Approval Workflow**

When the agent encounters an unknown question on a form (e.g., "What is your salary expectation?"), it follows this protocol:

1. **Snapshot & Pause**: The current browser session is frozen, the page DOM and screenshot are saved. The process is put into the SUSPENDED state.  
2. **Notification Dispatch**: The question, options, and screenshot are displayed on the Web GUI and sent to the user via Telegram.  
   * *Ex: "Backend Role - Salary Expectation? [3500€] [4000€] [Type Answer]"*  
3. **Persistence**: This task is marked in Postgres with the waiting_for_input flag. Meanwhile, the agent can switch to another task (Discovery or another application).  
4. **Resume**: When an answer is received via GUI or Telegram (Webhook or Polling), the relevant task returns to the PENDING state and the browser continues from where it left off (or via session restore).  
5. **Resume sequence follows this hierarchy**: 

1. Session Restore: The browser state is loaded via user_data_dir, the page navigates to the URL. 

2. DOM Validation: Checks if the expected form elements are still present.

3. Fallback — Form Restart: If the DOM has changed or the session expired, the form is filled out from the beginning. 

4. Fallback — Skip: If the above also fail, the task is set to PENDING_LATER, and a "Manual check required" notification is sent to the GUI and Telegram. 

## **3. Duplicate Prevention Layering**

Applying to the same posting twice is the biggest proof of being a "bot". Therefore, a 3-layer defense line is implemented:

### **Layer 1: Internal DB Check (Instant)**

* **Timing**: Right at the beginning of the Discovery phase.  
* **Logic**: URL_hash or Company_Role_hash check. If it exists in the DB, it is immediately eliminated.

### **Layer 2: Email Parsing (Intelligence)**

* **Timing**: Post-Discovery, Pre-Scoring.  
* **Logic**: "Application Received" or "Thank you for applying" emails from the last 30 days are scanned via Gmail/Outlook API (or MCP).  
* **Purpose**: To detect applications you made manually (outside the system).

### **Layer 3: Semantic Detection (LLM/Vector)**

* **Timing**: During the Scoring phase.  
* **Logic**: The description of the posting is projected into the vector space (Embedding). If there is a 95%+ similarity with previous applications, it is flagged as a "probable duplicate" and presented for approval, even if the title is different.

## **4. Daily Shutdown Protocol (Session Termination)**

Before the agent says "I'm done for today", it completes the following operations:

1. **Gmail Cleanup**: Parses confirmation emails received after applying, matches application IDs with the DB.  
2. **Analytics Update**:  
   * Total scanned postings.  
   * Submitted applications.  
   * Pending approvals.  
   * "Conversion Rate" (Match rate).  
3. **Cleanup**: Temporary browser profiles and caches are cleared.  
4. **Final Report (GUI & Telegram)**:  
   🚀 Session Complete.  
   -------------------  
   ✅ Applied: 12  
   ⏳ Pending Approval: 3  
   ❌ Rejected by Filter: 145  
   📈 Match Efficiency: 14%

   All operations are complete. You can safely shut down the system.

## **5. Critical Technical Constraints**

* **Rate Limiting**: A random.uniform(120, 600) second delay must be placed between each application.  
* **Human-in-the-loop**: If no response is received from the user (via GUI or Telegram) within 30 minutes, that application is "Skipped" and marked as PENDING_LATER.  
* **Stealth**: When using Playwright, the stealth_plugin must be active and the user-agent must be randomized in each session.
