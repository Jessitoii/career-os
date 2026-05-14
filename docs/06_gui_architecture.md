# **6. GUI Architecture & Specifications**

## **1. Overview**
Career OS features a comprehensive web-based Graphical User Interface (GUI) to provide complete visibility and control over the job application orchestration system. The GUI acts as the central command center, augmenting the Telegram bot for monitoring, reporting, and Human-in-the-Loop (HITL) interactions. Users can view everything from high-level statistics down to the granular state of a single application.

## **2. Technology Stack**
* **Frontend Framework:** Next.js (React) or Vue.js
* **Styling:** Tailwind CSS (or Vanilla CSS) with modern, dynamic UI elements (Dark Mode, animations, responsive design)
* **State Management:** React Context / Redux / Pinia
* **Communication:** REST APIs (FastAPI backend) and WebSockets for real-time live updates from the state machine (Celery/Redis)

## **3. Core Modules & Pages**

### **3.1. Dashboard (The Command Center)**
* **Live Stats:** Applications submitted today, pending approvals, rejection rate, and daily quota progress.
* **Activity Feed:** Real-time stream of what the agents are currently doing via WebSockets (e.g., "Scraping LinkedIn...", "Scoring Job X...", "Filling form on Greenhouse...").
* **Conversion Funnel:** Visual representation of Application -> Interview -> Offer metrics over time.

### **3.2. Job Pipeline (Kanban Board)**
* Visual management of jobs across different states: `DISCOVERED`, `SCORING`, `AWAITING_APPROVAL`, `EXECUTING`, `APPLIED`, `REJECTED`.
* Drag-and-drop capability to manually override states or trigger actions.

### **3.3. Human-in-the-Loop (HITL) Interface**
* A dedicated workspace for pending tasks that require human intervention.
* Displays the problem (e.g., "Missing Salary Expectation"), a screenshot of the target form, and input fields to provide the required data.
* **Learned Behavior Toggle:** Option to save the provided input as a permanent rule for future applications.

### **3.4. Profile & Configuration Management**
* Native UI to edit `user_profile.yaml` data directly from the browser.
* Upload, manage, and assign different CV versions and documents.
* Adjust scoring thresholds (auto_apply, ask_user), locations, blocked companies, and daily caps via interactive controls.

### **3.5. Analytics & Reports**
* Charts detailing application success rates based on platform (LinkedIn, Indeed, etc.).
* Comparative analytics for CV performance.
* Weekly and monthly trend summaries.

## **4. Interaction with Existing Systems**
* **Telegram Synergy:** The GUI provides a deeper, richer view, while Telegram serves as an instant notification and quick-approval channel. Both channels stay in sync.
* **Real-time Engine:** By leveraging WebSockets, the GUI reflects the Celery worker states instantly, allowing users to watch the application process unfold without refreshing the page.
