from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.application import Application
from app.models.job import JobListing

router = APIRouter()

# --- Dashboard Stats ---
@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_jobs = db.query(JobListing).count()
    total_apps = db.query(Application).count()
    # Detailed grouping logic would go here
    return {
        "total_jobs": total_jobs,
        "total_applications": total_apps,
    }

# --- Job Pipeline ---
@router.get("/applications/{application_id}/logs")
def get_application_logs(application_id: str, db: Session = Depends(get_db)):
    logs = db.query(InteractionLog).filter(InteractionLog.application_id == application_id).order_by(InteractionLog.timestamp.desc()).all()
    return logs

@router.post("/applications/{application_id}/approve")
def approve_application(application_id: str, db: Session = Depends(get_db)):
    from app.core.state_machine import transition_state, ApplicationStatus
    from app.agents.apply_worker import apply_to_job
    try:
        transition_state(db, application_id, ApplicationStatus.approved, actor="web_console")
        db.commit()
        apply_to_job.delay(application_id)
        return {"status": "success", "message": "Application approved and queued."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/applications/{application_id}/reject")
def reject_application(application_id: str, db: Session = Depends(get_db)):
    from app.core.state_machine import transition_state, ApplicationStatus
    try:
        transition_state(db, application_id, ApplicationStatus.rejected, actor="web_console")
        db.commit()
        return {"status": "success", "message": "Application rejected."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/system/pause")
def pause_system():
    from app.core.kill_switch import engage_kill_switch
    engage_kill_switch("Web Console Trigger")
    return {"status": "success", "message": "Global kill switch engaged."}

@router.post("/system/resume")
def resume_system():
    from app.core.kill_switch import disengage_kill_switch
    disengage_kill_switch()
    return {"status": "success", "message": "Automation resumed."}

@router.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    apps = db.query(Application).limit(50).all()
    return apps

@router.post("/applications/{app_id}/override")
def override_application_state(app_id: str, new_state: str, db: Session = Depends(get_db)):
    """API for the kanban drag-and-drop to manually override a state."""
    # Would call state_machine.transition_state
    return {"status": "ok", "app_id": app_id, "new_state": new_state}

# --- WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/activity")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # The client shouldn't send much, this is a downstream channel
    except WebSocketDisconnect:
        manager.disconnect(websocket)
