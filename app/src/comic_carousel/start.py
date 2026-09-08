"""Entry module for the launcher: start the loopback GUI, or run the CLI when files are given."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import webbrowser
from pathlib import Path

from .server import serve


def write_runtime_state(url: str) -> None:
    target = os.environ.get("GOOSNAV_RUNTIME_STATE")
    if not target:
        return
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".state-")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"schema_version": 1, "pid": os.getpid(), "url": url}, handle)
    os.replace(temp, path)


def main() -> int:
    if len(sys.argv) > 1:  # ./run.sh scan.jpg ... => headless batch
        from .__main__ import main as cli
        os.chdir(os.environ.get("GOOSNAV_CALLER_CWD") or os.getcwd())  # bootstrap moved into app/; paths are the caller's
        return cli(sys.argv[1:])
    host = os.environ.get("GOOSNAV_HOST", "127.0.0.1")
    port = int(os.environ.get("GOOSNAV_PORT_PREFERENCE") or 0)
    _app, server = serve(host, port)
    url = f"http://{host}:{server.server_port}/"
    write_runtime_state(url)
    print(f"Comic Carousel Generator is at {url}", flush=True)
    if not os.environ.get("GOOSNAV_LAUNCH_SESSION"):  # no supervisor: open the browser myself
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
