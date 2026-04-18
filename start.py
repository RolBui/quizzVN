import os
import traceback

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    print(f"Starting API on port {port}", flush=True)

    try:
        from app.main import app

        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception:
        print("Application failed to start.", flush=True)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
