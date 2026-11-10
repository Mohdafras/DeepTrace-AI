"""Run the real backend with disposable SQLite history for browser tests only."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def main():
    import uvicorn
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    with TemporaryDirectory(prefix="deeptrace-browser-") as directory:
        os.environ["DATABASE_PATH"] = str(Path(directory) / "history.db")
        # Import only after selecting the temporary database. This marker exists
        # only in this runner, never in the normal application's routes.
        from main import app
        from app.config import settings

        @app.get("/__test__/isolation", include_in_schema=False)
        def isolation():
            return {
                "purpose": "deeptrace-browser-tests",
                "disposable_history": settings.resolve(settings.database_path) == Path(directory) / "history.db",
            }

        print("Browser-test backend: real model, disposable history, port 8003", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")


if __name__ == "__main__":
    main()
