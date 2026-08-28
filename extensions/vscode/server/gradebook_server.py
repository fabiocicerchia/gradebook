"""Long-lived scan server for the gradebook VS Code extension.

Speaks newline-delimited JSON over stdin/stdout. One request per line in, one
response per line out; `id` correlates them.

Why a server at all, rather than shelling out to `gradebook-code --format json`:
a CLI run pays for interpreter startup and importing a 2,000-line module before
it reads a byte. At one run per save that is tolerable; at one run per keystroke
it is the dominant cost. Here it happens once per session.

Standard library only, like the two tools it drives — it imports them rather
than re-implementing anything, so `dependencies = []` still describes
everything that ships.

Ops:
  ping                        -> {protocol, versions, python, modules,
                                  severityOrder}
  scanProject {root, tool}    -> the full report for one tool over one directory
  invalidate  {}              -> drop the cached report(s)
  cancel      {cancel: id}    -> drop the answer to a scan no longer wanted
"""

import argparse
import importlib
import importlib.util
import json
import os
import queue
import sys
import threading
from pathlib import Path

PROTOCOL_VERSION = 1
TOOLS = ("code", "tests")

# extensions/vscode/server/ -> repo root, for a checkout with no install.
REPO_ROOT = Path(__file__).resolve().parents[3]


def load_tool(tool, module_path=None):
    """Import a gradebook module, preferring an explicit path.

    An explicit path wins, then an installed package, then the sibling folder
    in this checkout — so the extension works from pipx or from a clone.
    """
    name = f"gradebook_{tool}"
    if module_path:
        path = Path(module_path)
        return _from_path(name, path / f"{name}.py" if path.is_dir() else path)
    try:
        return importlib.import_module(name)
    except ImportError:
        return _from_path(name, REPO_ROOT / f"gradebook-{tool}" / f"{name}.py")


def _from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so a module that imports itself finds it.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The module surface this server calls. Checked at startup rather than
# discovered when a scan fails: an older gradebook imports perfectly and then
# raises `has no attribute 'severity_for'` on the first scan, which reads like a
# bug in the extension rather than a version to upgrade.
REQUIRED_API = ("collect", "evaluate", "recommendations", "FLAG_ORDER", "severity_for", "VERSION")


def missing_api(module):
    return [name for name in REQUIRED_API if not hasattr(module, name)]


class Server:
    def __init__(self, hints, out):
        # Loaded on demand, not up front: the two tools are separate packages,
        # and `tools: ["code"]` must not fail because the other one is absent.
        self.hints = hints
        self.modules = {}
        self.failures = {}
        self.out = out
        self.out_lock = threading.Lock()
        self.inbox = queue.Queue()
        # The last report per (root, tool). `invalidate` drops it; nothing here
        # serves a stale one, so this exists only so the client can ask again
        # without paying for a rescan it did not want.
        self.reports = {}
        self.cancelled = set()
        self.active_scan = None

    # --- transport -------------------------------------------------------

    def send(self, payload):
        line = json.dumps(payload, default=str)
        with self.out_lock:
            self.out.write(line + "\n")
            self.out.flush()

    def read_stdin(self):
        """Feed stdin lines to the inbox from a thread.

        A thread rather than `select()` because select cannot watch a pipe on
        Windows, and blocking readline releases the GIL anyway.
        """
        for line in sys.stdin:
            line = line.strip()
            if line:
                self.inbox.put(line)
        self.inbox.put(None)

    # --- modules ---------------------------------------------------------

    def module_for(self, tool):
        """The module for one tool, or a ValueError naming how to get it."""
        if tool in self.modules:
            return self.modules[tool]
        if tool in self.failures:
            raise ValueError(self.failures[tool])
        try:
            module = load_tool(tool, self.hints.get(tool))
            missing = missing_api(module)
            if missing:
                raise ImportError(
                    f"gradebook-{tool} at {getattr(module, '__file__', '?')} is too old for "
                    f"this extension: it has no {', '.join(missing)}"
                )
        except Exception as exc:  # noqa: BLE001 - turned into advice below
            self.failures[tool] = (
                f"gradebook-{tool} is not available ({exc}). Install it with "
                f"`pip install gradebook-{tool}`, or set `gradebook.{tool}Path` to the "
                f"folder holding gradebook_{tool}.py."
            )
            raise ValueError(self.failures[tool]) from exc
        self.modules[tool] = module
        return module

    def available(self):
        """Which tools load right now, without raising on the ones that do not."""
        loaded = {}
        for tool in TOOLS:
            try:
                loaded[tool] = self.module_for(tool)
            except ValueError:
                pass
        return loaded

    # --- scanning --------------------------------------------------------

    def scan_project(self, request):
        """Score one directory with one tool.

        Whole-repo, never per-file: hotspots need `git log` and duplication is
        cross-file, so `collect()` takes a directory and there is no meaningful
        single-file score to serve.
        """
        tool = request.get("tool", "code")
        module = self.module_for(tool)
        root = Path(request["root"])
        if not root.is_dir():
            raise NotADirectoryError(f"not a directory: {root}")
        report = module.evaluate(module.collect(root))
        report["recommendations"] = [
            {"dimension": d["id"], "points": d["lost"], "advice": d["advice"]}
            for d in module.recommendations(report, request.get("top", 5))
        ]
        report["tool"] = f"gradebook-{tool}"
        report["version"] = module.VERSION
        self.reports[(str(root), tool)] = report
        return {"report": report}

    def severity_order(self, loaded):
        """Every kind an available tool knows, bucketed — no client keeps a copy."""
        order = {}
        for module in loaded.values():
            for kind in module.FLAG_ORDER:
                order[kind] = module.severity_for(kind)
        return order

    # --- dispatch --------------------------------------------------------

    def handle(self, request):
        op = request.get("op")
        if op == "ping":
            loaded = self.available()
            return {
                "protocol": PROTOCOL_VERSION,
                "python": sys.version.split()[0],
                "versions": {tool: m.VERSION for tool, m in loaded.items()},
                "modules": {tool: getattr(m, "__file__", None) for tool, m in loaded.items()},
                # Named rather than implied by absence: "not installed" and
                # "installed but broken" need different advice, and a client
                # that cannot tell them apart says neither.
                "unavailable": dict(self.failures),
                # The ranking is gradebook's to decide, so it is published
                # rather than reinvented over there — a kind added to
                # FLAG_ORDER needs no change in the extension.
                "severityOrder": self.severity_order(loaded),
            }
        if op == "scanProject":
            return self.scan_project(request)
        if op == "invalidate":
            self.reports.clear()
            return {"cached": 0}
        if op == "cancel":
            target = request.get("cancel")
            if target is None:
                return {"cancelling": False}
            # A cancel that arrives after its scan finished names no scan at
            # all; drop it rather than keep it for the life of the process.
            if target == self.active_scan:
                self.cancelled.add(target)
            return {"cancelling": target in self.cancelled}
        raise ValueError(f"unknown op: {op!r}")

    def parse(self, line):
        try:
            return json.loads(line)
        except ValueError as exc:
            self.send({"id": None, "ok": False, "error": f"malformed request: {exc}"})
            return None

    def dispatch(self, request):
        request_id = request.get("id")
        self.active_scan = request_id if request.get("op") == "scanProject" else None
        try:
            response = self.handle(request)
        # A bad request is one failed request, not the end of the session, so
        # it comes back as an error the extension can surface.
        except (Exception, SystemExit) as exc:  # noqa: BLE001 - reported, not swallowed
            self.active_scan = None
            self.send({"id": request_id, "ok": False, "error": f"{exc}"})
            return
        self.active_scan = None
        if request_id in self.cancelled:
            # ponytail: cancel drops the answer, it does not interrupt the scan
            # — a full scan is ~0.25s. Make collect() interruptible if that
            # stops holding.
            self.cancelled.discard(request_id)
            return
        response["id"] = request_id
        response["ok"] = True
        self.send(response)

    def serve(self):
        threading.Thread(target=self.read_stdin, daemon=True).start()
        self.send({"id": 0, "ok": True, "event": "ready", "protocol": PROTOCOL_VERSION})
        while True:
            line = self.inbox.get()
            if line is None:
                break
            request = self.parse(line)
            if request is not None:
                self.dispatch(request)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="gradebook_server")
    parser.add_argument("--code", help="path to gradebook_code.py or its directory")
    parser.add_argument("--tests", help="path to gradebook_tests.py or its directory")
    args = parser.parse_args(argv)

    # Nothing but protocol on stdout. Anything that prints — a warning from an
    # import, a stray debug line — would otherwise land mid-stream and
    # desynchronise the parser on the other end.
    out = sys.stdout
    sys.stdout = sys.stderr

    # Resolved, not loaded: whether a tool is importable is a per-request
    # answer, so that asking for one missing tool does not take the other down
    # with it. Only something unrecoverable is fatal here.
    hints = {
        tool: getattr(args, tool) or os.environ.get(f"GRADEBOOK_{tool.upper()}_MODULE")
        for tool in TOOLS
    }
    try:
        server = Server(hints, out)
    except Exception as exc:  # noqa: BLE001 - the extension turns this into a prompt
        out.write(json.dumps({"id": 0, "ok": False, "fatal": True, "error": f"{exc}"}) + "\n")
        out.flush()
        return 1

    server.serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
