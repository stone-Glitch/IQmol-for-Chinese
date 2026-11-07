#!/usr/bin/env python3
"""Smoke test for the IQmol local control channel.

Usage:
    python3 scripts/iqmol_control_smoke.py [sample-file ...]

With no arguments it only exercises the process-level commands (ping/state)
and the rejection paths. Pass one or more structure files to also test load.

The channel is opt-in at runtime: it starts automatically unless the
IQMOL_NO_CONTROL environment variable is set.
"""

import json
import os
import socket
import sys
import time

DISCOVERY = "iqmol-ctrl.json"


def discovery_paths():
    """The same places ControlServer looks, most likely first."""
    paths = []
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        paths.append(os.path.join(runtime, DISCOVERY))
    paths.append("/tmp/runtime-root/" + DISCOVERY)   # XDG fallback used by Qt
    paths.append("/tmp/" + DISCOVERY)
    return paths


class Client:
    def __init__(self, endpoint, token, timeout=45.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(endpoint)
        self.token = token
        self.buf = b""
        self.seq = 0

    def call(self, cmd, args=None):
        self.seq += 1
        request = {
            "v": 1,
            "id": "smoke-%d" % self.seq,
            "token": self.token,
            "cmd": cmd,
            "args": args or {},
        }
        self.sock.sendall(json.dumps(request).encode() + b"\n")
        while b"\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("connection closed without a reply")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return json.loads(line.decode())

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Report:
    def __init__(self):
        self.cases = []

    def add(self, ok, label, detail=""):
        self.cases.append((ok, label, detail))
        print("[%s] %-26s %s" % ("PASS" if ok else "FAIL", label, detail))

    def expect_ok(self, label, reply, **want):
        body = reply.get("result", {})
        ok = reply.get("ok") is True
        detail = json.dumps(body, ensure_ascii=False)
        for key, value in want.items():
            if body.get(key) != value:
                ok = False
                detail += "  (expected %s=%r)" % (key, value)
        self.add(ok, label, detail)

    def expect_error(self, label, reply, code):
        err = reply.get("error", {})
        ok = reply.get("ok") is False and err.get("code") == code
        self.add(ok, label, "%s: %s" % (err.get("code"), err.get("message")))

    def summary(self):
        failed = [c for c in self.cases if not c[0]]
        print()
        print("RESULT: %d/%d passed" % (len(self.cases) - len(failed),
                                        len(self.cases)))
        return 0 if not failed else 1


def main(argv):
    report = Report()

    info = None
    for path in discovery_paths():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                info = json.load(fh)
            mode = os.stat(path).st_mode & 0o777
            print("discovery : %s (mode %o)" % (path, mode))
            break

    if not info:
        print("control channel is not running; start IQmol first")
        print("looked in:", ", ".join(discovery_paths()))
        return 2

    print("endpoint  : %s" % info["endpoint"])
    print("pid       : %s" % info["pid"])
    print("token     : %s..." % info["token"][:8])
    print()

    client = Client(info["endpoint"], info["token"])

    report.expect_ok("ping", client.call("ping"), pong=True)

    reply = client.call("state")
    report.expect_ok("state", reply)
    if reply.get("ok"):
        body = reply["result"]
        print("             version=%s tag=%s" % (body.get("version"),
                                                  body.get("tag")))

    report.expect_error("load without path", client.call("load", {}), "BAD_ARGS")
    report.expect_error("load missing file",
                        client.call("load", {"path": "/nonexistent.xyz"}),
                        "LOAD_FAILED")
    report.expect_error("unknown command", client.call("nope"), "BAD_COMMAND")

    for sample in argv:
        started = time.time()
        reply = client.call("load", {"path": os.path.abspath(sample)})
        report.expect_ok("load %s" % os.path.basename(sample), reply, loaded=True)
        print("             %.2fs" % (time.time() - started))

    if argv:
        reply = client.call("state")
        report.expect_ok("state after load", reply)

    client.close()

    # An unauthorised client must get a dropped connection and no JSON.
    probe = Client(info["endpoint"], "0" * 32, timeout=5.0)
    try:
        probe.sock.sendall(b'{"v":1,"id":"x","token":"bad","cmd":"ping"}\n')
        data = probe.sock.recv(4096)
        ok = not data
        note = "disconnected without replying" if ok else "got a reply: %r" % data
    except (socket.timeout, ConnectionResetError, OSError) as exc:
        ok = True
        note = type(exc).__name__
    finally:
        probe.close()

    print("[%s] %-26s %s" % ("PASS" if ok else "FAIL", "wrong token", note))
    report.cases.append((ok, "wrong token", note))

    return report.summary()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
