from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import hello, images, jobs

app = FastAPI(title="Music Visualizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hello.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")

# Serve the built frontend (run `npm run build` in frontend/). Mounted last so
# the /api routes and /docs take precedence.
if settings.frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
