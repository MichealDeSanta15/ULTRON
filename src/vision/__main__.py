from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from pathlib import Path

from .config import Settings
from .runtime import VisionRuntime
from .server import VisionHTTPServer, VisionRequestHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the VISION multi-agent command center")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--check", action="store_true", help="Run a configuration health check")
    args = parser.parse_args()

    settings = Settings.from_environment(host=args.host, port=args.port)
    runtime = VisionRuntime(settings)

    if args.check:
        print(json.dumps(runtime.health(), indent=2))
        return

    server = VisionHTTPServer((settings.host, settings.port), VisionRequestHandler, runtime)
    runtime.log_event("system", "VISION online", {"address": f"http://{settings.host}:{settings.port}"})
    url = f"http://{settings.host}:{settings.port}"
    print(f"VISION online at {url}")
    print("Press Ctrl+C to stop.")
    if args.open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nVISION shutting down.")
    finally:
        server.server_close()
        runtime.close()


if __name__ == "__main__":
    main()
