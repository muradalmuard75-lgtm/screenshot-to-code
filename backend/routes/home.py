import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter()

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
index_file = os.path.join(frontend_dist, "index.html")


@router.get("/")
async def get_status():
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse(
        content="<h3>Your backend is running correctly. Please open the front-end URL (default is http://localhost:5173) to use screenshot-to-code.</h3>"
    )
