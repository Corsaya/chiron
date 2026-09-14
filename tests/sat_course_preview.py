"""Synthetic-only Classroom preview: python -m tests.sat_course_preview."""
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import classroom_routes
from src.auth_helpers import require_user
from tests.test_sat_course import HOME


@asynccontextmanager
async def lifespan(app):
    original = classroom_routes.COURSES_ROOT
    with TemporaryDirectory(prefix="chiron-sat-preview-") as directory:
        root = Path(directory) / "SAT"
        (root / "Current").mkdir(parents=True)
        (root / "Home.md").write_text(HOME)
        (root / "Current/Practice.md").write_text("# Practice\nSynthetic exercise.\n")
        (root / "Current/Review.md").write_text("# Review\nSynthetic observations.\n")
        classroom_routes.COURSES_ROOT = directory
        try:
            yield
        finally:
            classroom_routes.COURSES_ROOT = original


app = FastAPI(lifespan=lifespan)
# Authentication is exercised by the route tests; this isolated preview has no real records.
app.dependency_overrides[require_user] = lambda: "synthetic-preview"
app.include_router(classroom_routes.setup_classroom_routes())
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parents[1] / "static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8768)
