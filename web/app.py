from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.routes import router, storage


PROJECT_ROOT = Path(__file__).parents[1]
STATIC_DIR = PROJECT_ROOT / "web" / "static"

app = FastAPI(title="API Test Framework", version="0.1.0")
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/run-files", StaticFiles(directory=storage.runs), name="run-files")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
