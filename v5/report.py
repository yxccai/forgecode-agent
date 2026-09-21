"""Generate a reviewable, credential-free report from persisted benchmark metrics."""
import argparse
import json
from pathlib import Path

from v5.evaluate import summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/evaluation-v5.md"))
    parser.add_argument("--replacement-directory", type=Path,
                        help="Use corrected runs from this directory, retaining both raw datasets")
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.directory / "results.jsonl").read_text().splitlines()]
    manifest = json.loads((args.directory / "manifest.json").read_text())
    replacements = []
    if args.replacement_directory:
        replacement_manifest = json.loads((args.replacement_directory / "manifest.json").read_text())
        for key in ("dataset_sha256", "model", "reasoning_effort"):
            if manifest[key] != replacement_manifest[key]:
                raise ValueError("Replacement experiment does not match " + key)
        replacements = [json.loads(line) for line in
                        (args.replacement_directory / "results.jsonl").read_text().splitlines()]
        keys = {(r["task"], r["variant"], r["repeat"]) for r in replacements}
        rows = [r for r in rows if (r["task"], r["variant"], r["repeat"]) not in keys] + replacements
        manifest["corrected_runs"] = len(replacements)
    summary = summarize(rows)
    lines = ["# V5 evaluation results", "", f"Completed runs: {len(rows)} / {manifest['jobs']}.",
             f"Model: `{manifest['model']}`. Reasoning effort: `{manifest['reasoning_effort']}` (null means provider default).",
             f"Dataset SHA-256: `{manifest['dataset_sha256']}`.",
             "", "## Aggregate metrics", "",
             "| Variant | N | Task success | Test pass | Steps | Tools | Tokens | Seconds | Files read |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, result in summary.items():
        lines.append(f"| {name} | {result['tasks']} | {result['success_rate']:.1%} | "
                     f"{result['test_pass_rate']:.1%} | {result['mean_steps']:.2f} | "
                     f"{result['mean_tool_calls']:.2f} | {result['mean_tokens']:.0f} | "
                     f"{result['mean_latency_seconds']:.2f} | {result['mean_files_read']:.2f} |")
    lines += ["", "Full uses 20 tasks; ablations use the same fixed 5-task subset. Do not directly compare unpaired means.",
              "", "## Paired differences", "", "Deltas are ablation minus full on matching task/repeat pairs.", "",
              "| Variant | Pairs | Success delta | Token delta | Seconds delta |",
              "|---|---:|---:|---:|---:|"]
    for name, result in summary.items():
        if "paired" in result:
            pair = result["paired"]
            lines.append(f"| {name} | {pair['n']} | {pair['success_delta']:+.1%} | "
                         f"{pair['token_delta']:+.0f} | {pair['latency_delta']:+.2f} |")
    lines += ["", "## Per-run outcomes", "",
              "| Task | Variant | Success | Tests | Failure | Tokens | Seconds |",
              "|---|---|---|---|---|---:|---:|"]
    for row in sorted(rows, key=lambda r: (r["task"], r["variant"], r["repeat"])):
        lines.append(f"| {row['task']} | {row['variant']} | {row['success']} | "
                     f"{row['tests_passed']}/{row['tests_total']} | {row['failure'] or '-'} | "
                     f"{row['tokens']} | {row['latency_seconds']:.2f} |")
    lines += ["", "## Interpretation limits", "",
              f"Corrected reruns: {len(replacements)}. The first no-verification pilot omitted the task-level test reminder; "
              "corrected runs use exactly the same task prompt as full. Both raw datasets remain local.",
              "These are authored, small Python tasks with 24 distractor modules, not a production-repository benchmark.",
              "One repeat and five paired tasks per ablation cannot establish statistical significance or broad superiority.",
              "Memory is standardized source-backed repository orientation, not recalled hidden answers or natural longitudinal task history.",
              "No-verification disables the runtime's mandatory baseline/final repair loop; the model may still choose test tools.",
              "Latency includes network and concurrent API scheduling. Token counts come from provider usage, not local estimates.",
              "Failures are classified conservatively: code_or_edit, verification, termination, verification_tampering, infrastructure.",
              "A successful verifier proves the supplied cases passed, not general correctness or security sandboxing.", ""]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines))
    public = args.output.parent / "evaluation-v5.json"
    public.write_text(json.dumps({"manifest": manifest, "summary": summary, "runs": rows}, indent=2))
    print(f"Report: {args.output}; structured metrics: {public}")


if __name__ == "__main__":
    main()
