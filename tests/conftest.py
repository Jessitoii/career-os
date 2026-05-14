import pytest
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Mock Server
app = FastAPI(title="Mock ATS Server")

@app.get("/greenhouse/job/123", response_class=HTMLResponse)
def mock_greenhouse():
    return """
    <html>
        <div id="header">Greenhouse Mock</div>
        <form>
            <input type="text" id="first_name" name="first_name">
            <input type="text" id="last_name" name="last_name">
            <input type="email" id="email" name="email">
            <input type="file" name="resume">
            <button id="submit_app" type="button">Submit Application</button>
        </form>
    </html>
    """

@app.get("/greenhouse/captcha", response_class=HTMLResponse)
def mock_greenhouse_captcha():
    return """
    <html>
        <body>
            <iframe src="https://recaptcha.net/recaptcha/api2/anchor"></iframe>
        </body>
    </html>
    """

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=9999, log_level="error")

@pytest.fixture(scope="session", autouse=True)
def mock_server():
    """Spins up a background mock server before tests run."""
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    import time
    time.sleep(2) # Give it time to boot
    yield
