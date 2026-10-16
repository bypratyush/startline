"""Registration-rush load generator for the HPA demo.

Simulates the minute a big race opens entries: many athletes searching events
with recommendations on (the most CPU-heavy endpoint, it scores every event for
the athlete's profile) and running the readiness calculator.

Runs inside the cluster (scripts/registration-rush.sh) or anywhere with:
    TARGET=http://localhost:8000 DURATION=60 CONCURRENCY=8 python3 scripts/loadgen.py
Standard library only, so it runs in the backend image without extra packages.
"""

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request

TARGET = os.environ.get("TARGET", "http://startline-backend:8000").rstrip("/")
DURATION = int(os.environ.get("DURATION", "180"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "8"))

PROFILES = [
    {"name": "Load Runner", "city": "mumbai", "sports": [{"sport": "running", "answers": {
        "level": "intermediate", "run_longest_recent": "11to21", "run_5k_band": "27to33"}}]},
    {"name": "Load Swimmer", "city": "bengaluru", "sports": [{"sport": "swimming", "answers": {
        "level": "beginner", "swim_nonstop": "400to1000", "swim_openwater": "some"}}, {"sport": "triathlon", "answers": {
        "level": "beginner", "tri_experience": "none", "tri_weakest": "swim"}}]},
    {"name": "Load Rider", "city": "pune", "sports": [{"sport": "cycling", "answers": {
        "level": "advanced", "cyc_longest_ride": "121to200", "cyc_speed": "23to27"}}]},
]

stats = {"ok": 0, "err": 0, "latency": 0.0}
lock = threading.Lock()


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(TARGET + path, data=data, method=method,
                                 headers={"content-type": "application/json"} if data else {})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read() or b"null")
        ok = True
    except (urllib.error.URLError, TimeoutError):
        payload, ok = None, False
    with lock:
        stats["ok" if ok else "err"] += 1
        stats["latency"] += time.perf_counter() - start
    return payload


def worker(athletes, deadline):
    while time.time() < deadline:
        a = random.choice(athletes)
        sports = ",".join(s["sport"]["slug"] for s in a["sports"])
        call("GET", f"/api/events?athlete_id={a['id']}&sport={sports}&recommend=true")
        if random.random() < 0.2:
            call("GET", f"/api/events?athlete_id={a['id']}&recommend=true")


def main():
    athletes = [a for a in (call("POST", "/api/athletes", p) for p in PROFILES) if a]
    if not athletes:
        raise SystemExit(f"could not create load-test profiles at {TARGET}")
    deadline = time.time() + DURATION
    print(f"rush: {CONCURRENCY} workers for {DURATION}s against {TARGET}", flush=True)
    threads = [threading.Thread(target=worker, args=(athletes, deadline), daemon=True) for _ in range(CONCURRENCY)]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        time.sleep(15)
        with lock:
            n = stats["ok"] + stats["err"]
            avg = stats["latency"] / n if n else 0
            print(f"  requests={n} errors={stats['err']} avg_latency={avg * 1000:.0f}ms", flush=True)
    for a in athletes:
        call("DELETE", f"/api/athletes/{a['id']}")
    print("done", json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
