"""Run a local, repeatable evaluation without calling a model."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from .evaluate import Result, evaluate, load_cases, load_replies


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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
    args = parser.parse_args()
    if not 0 <= args.min_grounded <= 1:
        parser.error("--min-grounded must be between 0 and 1")
    if not 0 <= args.min_abstention <= 1:
        parser.error("--min-abstention must be between 0 and 1")
    try:
        cases = load_cases(read(args.cases))
        snapshot = args.sources.read_bytes()
        sources = json.loads(snapshot.decode("utf-8"))["repositories"]
        results = evaluate(cases, sources, load_replies(read(args.replies)))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    grouped: dict[str, list[Result]] = {"answerable": [], "requires_abstention": []}
    for case, result in zip(cases, results, strict=True):
        kind = "requires_abstention" if case.repository is None else "answerable"
        grouped[kind].append(result)

    totals = summarize(results)
    by_case_type = {name: summarize(group) for name, group in grouped.items()}
    abstentions = by_case_type["requires_abstention"]
    if args.min_abstention and not abstentions["total"]:
        parser.error("--min-abstention requires at least one abstention case")
    source_sha256 = sha256(snapshot).hexdigest()
    if args.format == "text":
        for name, counts in {"overall": totals, **by_case_type}.items():
            print(f"{name}: {counts['correct']}/{counts['total']} correct, {counts['grounded']}/{counts['total']} grounded")
        print(f"source_sha256: {source_sha256}")
        for result in results:
            print(f"{result.id}: {result.reason}")
    else:
        print(json.dumps({
            **totals,
            "by_case_type": by_case_type,
            "source_sha256": source_sha256,
            "results": [asdict(result) for result in results],
        }, indent=2))
    below_grounded = totals["grounded"] / totals["total"] < args.min_grounded
    below_abstention = (abstentions["total"] > 0
                        and abstentions["grounded"] / abstentions["total"] < args.min_abstention)
    return int(below_grounded or below_abstention)


if __name__ == "__main__":
    raise SystemExit(main())
