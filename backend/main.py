# Load environment variables first
from dotenv import load_dotenv

load_dotenv()


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import IS_DEBUG_ENABLED
from routes import (
    capabilities,
    screenshot,
    generate_code,
    home,
    evals,
    export,
    design_systems,
    prompt_reports,
    agent_runs,
    eval_sets,
)
from uploaded_assets import configure_uploaded_asset_routes

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
configure_uploaded_asset_routes(app)


@app.on_event("startup")
async def log_debug_mode() -> None:
    debug_status = "ENABLED" if IS_DEBUG_ENABLED else "DISABLED"
    print(f"Backend startup complete. Debug mode is {debug_status}.")


@app.on_event("startup")
async def probe_screenshot_preview_on_startup() -> None:
    # Detect (and warm up) headless Chromium so the screenshot_preview tool is
    # only offered when it can actually run. Logs the outcome.
    from preview_screenshot import probe_screenshot_preview

    await probe_screenshot_preview()

import os
import time
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

DEPLOY_TIMESTAMP = int(time.time())

# Configure CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    # Never cache anything so any update appears instantly on mobile/desktop browsers
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    if "etag" in response.headers:
        del response.headers["etag"]
    if "last-modified" in response.headers:
        del response.headers["last-modified"]
    return response


@app.get("/api/version")
async def get_app_version():
    return JSONResponse(
        content={"version": DEPLOY_TIMESTAMP},
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

# Add routes
app.include_router(generate_code.router)
app.include_router(screenshot.router)
app.include_router(capabilities.router)
app.include_router(evals.router)
app.include_router(export.router)
app.include_router(design_systems.router)
app.include_router(prompt_reports.router)
app.include_router(agent_runs.router)
app.include_router(eval_sets.router)

# Mount frontend dist if built (enables single-service deployment on Render/cloud)
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        # Force cache-busting on every load so any modification appears instantly
        cache_buster = f"?v={int(time.time())}"
        content = content.replace('.js"', f'.js{cache_buster}"').replace('.css"', f'.css{cache_buster}"')
        content = content.replace('BUILD_PLACEHOLDER', str(DEPLOY_TIMESTAMP))
        return HTMLResponse(
            content=content,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0, post-check=0, pre-check=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "Clear-Site-Data": '"cache"',
            },
        )
    return HTMLResponse("<h3>Backend running</h3>")

if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    app.include_router(home.router)

