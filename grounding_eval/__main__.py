"""Run a local, repeatable evaluation without calling a model."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from .evaluate import Result, evaluate, load_cases, load_replies


def read_snapshot(path: Path):
    data = path.read_bytes()
    return json.loads(data.decode("utf-8")), sha256(data).hexdigest()


def summarize(results: list[Result]) -> dict[str, int]:
    return {
        "total": len(results),
        "correct": sum(result.correct for result in results),
        "grounded": sum(result.grounded for result in results),
    }


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("replies", type=Path, help="JSON array of model replies")
    parser.add_argument("--cases", type=Path, default=Path("fixtures/cases.json"))
    parser.add_argument("--sources", type=Path, default=Path("fixtures/repositories.json"))
    parser.add_argument("--min-grounded", type=float, default=0, help="Fail below this fraction (0 to 1)")
    parser.add_argument("--min-abstention", type=float, default=0, help="Minimum grounded fraction for abstentions (0 to 1)")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--require-all-replies", action="store_true", help="fail if any case has no reply")
    parser.add_argument("--output", type=Path, help="write the report to this file instead of stdout")
    args = parser.parse_args()
    if not 0 <= args.min_grounded <= 1:
        parser.error("--min-grounded must be between 0 and 1")
    if not 0 <= args.min_abstention <= 1:
        parser.error("--min-abstention must be between 0 and 1")
    try:
        case_data, cases_sha256 = read_snapshot(args.cases)
        snapshot, source_sha256 = read_snapshot(args.sources)
        reply_data, replies_sha256 = read_snapshot(args.replies)
        cases = load_cases(case_data)
        replies = load_replies(reply_data)
        results = evaluate(cases, snapshot["repositories"], replies)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    grouped: dict[str, list[Result]] = {"answerable": [], "requires_abstention": []}
    for case, result in zip(cases, results, strict=True):
        kind = "requires_abstention" if case.repository is None else "answerable"
        grouped[kind].append(result)

    missing_count = sum(case.id not in replies for case in cases)
    totals = summarize(results)
    by_case_type = {name: summarize(group) for name, group in grouped.items()}
    abstentions = by_case_type["requires_abstention"]
    if args.min_abstention and not abstentions["total"]:
        parser.error("--min-abstention requires at least one abstention case")
    digests = {"source_sha256": source_sha256, "cases_sha256": cases_sha256, "replies_sha256": replies_sha256}
    if args.format == "text":
        lines = [
            f"{name}: {counts['correct']}/{counts['total']} correct, {counts['grounded']}/{counts['total']} grounded"
            for name, counts in {"overall": totals, **by_case_type}.items()
        ]
        lines.extend(f"{name}: {digest}" for name, digest in digests.items())
        lines.extend(f"{result.id}: {result.reason}" for result in results)
        report = "\n".join(lines)
    else:
        report = json.dumps({
            **totals,
            "by_case_type": by_case_type,
            **digests,
            "results": [asdict(result) for result in results],
        }, indent=2)
    if args.output is None:
        print(report)
    else:
        try:
            with args.output.open("x", encoding="utf-8", newline="\n") as file:
                file.write(report + "\n")
        except OSError as error:
            parser.error(str(error))
    below_grounded = totals["grounded"] / totals["total"] < args.min_grounded
    below_abstention = (abstentions["total"] > 0
                        and abstentions["grounded"] / abstentions["total"] < args.min_abstention)
    return int(below_grounded or below_abstention or (args.require_all_replies and missing_count > 0))


if __name__ == "__main__":
    raise SystemExit(main())
