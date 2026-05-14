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
