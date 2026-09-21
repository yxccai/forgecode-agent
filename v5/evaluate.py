import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tempfile
import time

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from forgecode.config import Config
from forgecode.trace import Trace
from v1.model import Model
from v4.agent import Runtime, initial
from v4.memory import Memory
from v4.tools import Tools
from v4.workspace import Workspace, git
from v5.oracle import evaluate_source, test_source
from v5.tasks import TASKS, PAIRED_IDS


VARIANTS = {"full": {}, "no_planning": {"planning": False},
            "no_context": {"repo_context": False}, "no_verification": {"verification": False},
            "no_memory": {"memory": False}}


def create_fixture(root, task):
    Path(root, "subject.py").write_text(task.source)
    Path(root, "test_public.py").write_text(test_source(task, task.cases[:1]))
    Path(root, ".gitignore").write_text(".forgecode/\n__pycache__/\n")
    for index in range(24):
        Path(root, f"module_{index}.py").write_text(f"def unrelated_{index}(x):\n    return x * {index+1}\n")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "-c", "user.name=Benchmark", "-c", "user.email=benchmark@example.invalid", "commit", "-qm", "fixture")


def run_one(task, variant, config, out, repeat=0):
    flags = {"planning": True, "repo_context": True, "verification": True, "memory": True,
             **VARIANTS[variant]}
    identity = f"{task.id}-{variant}-{repeat}"
    events, started = [], time.perf_counter()
    status, failure, scoring = "error", None, {"success": False, "passed": 0, "total": len(task.cases)}
    result = {}
    with tempfile.TemporaryDirectory(prefix="forgecode-eval-") as folder:
        try:
            create_fixture(folder, task)
            workspace = Workspace(folder, "eval")
            verify = ["python3", "-m", "unittest", "discover"]
            workspace.create(verify)
            # Standardized source-backed orientation, never an answer or previous held-out result.
            Memory(folder).remember("Repository conventions: implementation is subject.py; public tests "
                                    "are test_public.py. Run python3 -m unittest discover. " + task.id,
                                    ["subject.py", "test_public.py"], confidence=.8)
            tools = Tools(workspace.path, repo_context=flags["repo_context"], memory=flags["memory"], store_root=folder)
            trace = Trace(out / "traces" / f"{identity}.jsonl", events.append)
            with SqliteSaver.from_conn_string(":memory:") as saver:
                graph = Runtime(Model(config), tools, trace, flags["planning"]).build(saver)
                prompt = task.instruction + " Change subject.py only. Inspect source before editing. "
                prompt += "Do not change test_public.py. Finish with a concise summary."
                prompt += " Run python3 -m unittest discover to verify."
                state = initial(prompt, str(workspace.path), verify, max_steps=12, max_calls=30,
                                max_repairs=2, verification=flags["verification"])
                opts = {"configurable": {"thread_id": identity}, "recursion_limit": 200}
                result = graph.invoke(state, opts)
                while result.get("__interrupt__"):
                    argv = result["__interrupt__"][0].value.get("argv")
                    result = graph.invoke(Command(resume=argv == verify), opts)
                status = result["status"]
            source = (workspace.path / "subject.py").read_text()
            scoring = evaluate_source(task, source)
            if git(workspace.path, "diff", "--", "test_public.py"):
                scoring["success"] = False
                failure = "verification_tampering"
            if status not in {"verified", "answered"}:
                scoring["success"] = False
                failure = "termination" if status == "budget_exhausted" else "verification"
            if not scoring["success"] and failure is None:
                failure = "code_or_edit"
        except Exception as exc:
            failure = "infrastructure"
            # Do not log provider error strings, which can include credentials or endpoint URLs.
            result["exception_type"] = type(exc).__name__
    usage = [e for e in events if e["type"] == "usage"]
    reads = {e["args"].get("path") for e in events if e["type"] == "tool_start" and e["name"] == "read_file"}
    return {"task": task.id, "category": task.category, "variant": variant, "repeat": repeat,
            "success": scoring["success"], "tests_passed": scoring["passed"], "tests_total": scoring["total"],
            "status": status, "failure": failure, "exception_type": result.get("exception_type"),
            "steps": sum(e["type"] == "model_start" for e in events),
            "tool_calls": sum(e["type"] == "tool_end" for e in events),
            "tokens": sum(e.get("total_tokens", 0) for e in usage),
            "input_tokens": sum(e.get("input_tokens", 0) for e in usage),
            "usage_reported": bool(usage), "latency_seconds": round(time.perf_counter()-started, 3),
            "files_read": len(reads), "verification_runs": sum(e["type"] == "verification" for e in events),
            "memory_hits": sum(e.get("hits", 0) for e in events if e["type"] == "memory")}


def summarize(rows):
    report = {}
    for variant in VARIANTS:
        sample = [r for r in rows if r["variant"] == variant]
        if not sample:
            continue
        n = len(sample)
        report[variant] = {"tasks": n, "success_rate": sum(r["success"] for r in sample)/n,
                           "test_pass_rate": sum(r["tests_passed"] for r in sample)/sum(r["tests_total"] for r in sample)}
        for key in ("steps", "tool_calls", "tokens", "input_tokens", "latency_seconds", "files_read"):
            report[variant]["mean_" + key] = sum(r[key] for r in sample)/n
        report[variant]["failures"] = {kind: sum(r["failure"] == kind for r in sample)
                                       for kind in sorted({r["failure"] for r in sample if r["failure"]})}
        pairs = [(r, base) for r in sample for base in rows if base["variant"] == "full"
                 and base["task"] == r["task"] and base["repeat"] == r["repeat"]]
        if variant != "full" and pairs:
            report[variant]["paired"] = {"n": len(pairs),
                "success_delta": sum(int(r["success"])-int(b["success"]) for r,b in pairs)/len(pairs),
                "token_delta": sum(r["tokens"]-b["tokens"] for r,b in pairs)/len(pairs),
                "latency_delta": sum(r["latency_seconds"]-b["latency_seconds"] for r,b in pairs)/len(pairs)}
    return report


def main():
    parser = argparse.ArgumentParser(description="ForgeCode benchmark: real model, independent acceptance")
    parser.add_argument("--out", default=".forgecode/evaluation")
    parser.add_argument("--config")
    parser.add_argument("--windows-env", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--suite", choices=("smoke", "full", "matrix"), default="matrix")
    parser.add_argument("--variant", choices=tuple(VARIANTS), help="Run only this variant")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4 or args.repeats < 1:
        parser.error("workers must be 1-4; repeats must be positive")
    if args.windows_env:
        from forgecode.windows import windows_environment
        windows_environment()
    config = Config.load(args.config)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    selected = TASKS[:1] if args.suite == "smoke" else TASKS
    for repeat in range(args.repeats):
        jobs.extend((task, "full", repeat) for task in selected)
        if args.suite == "matrix":
            jobs.extend((task, variant, repeat) for task in TASKS if task.id in PAIRED_IDS
                        for variant in VARIANTS if variant != "full")
    if args.variant:
        jobs = [job for job in jobs if job[1] == args.variant]
    fingerprint = hashlib.sha256(json.dumps([asdict(t) for t in TASKS], sort_keys=True).encode()).hexdigest()
    metadata = {"suite": args.suite, "dataset_sha256": fingerprint, "model": config.model,
                "reasoning_effort": config.reasoning_effort, "workers": args.workers,
                "repeats": args.repeats, "jobs": len(jobs), "seed": 42}
    if args.variant:
        metadata["variant"] = args.variant
    manifest = out / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()) != metadata:
        raise ValueError("Output directory belongs to another evaluation configuration")
    manifest.write_text(json.dumps(metadata, indent=2))
    results = out / "results.jsonl"
    rows = [json.loads(line) for line in results.read_text().splitlines()] if results.exists() else []
    done = {(r["task"], r["variant"], r["repeat"]) for r in rows}
    jobs = [j for j in jobs if (j[0].id, j[1], j[2]) not in done]
    random.Random(42).shuffle(jobs)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, task, variant, config, out, repeat) for task,variant,repeat in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            with results.open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
            (out / "summary.json").write_text(json.dumps(summarize(rows), indent=2))
    (out / "summary.json").write_text(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
