"""Run a local, repeatable evaluation without calling a model."""

from argparse import ArgumentParser
from dataclasses import asdict
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
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    if not 0 <= args.min_grounded <= 1:
        parser.error("--min-grounded must be between 0 and 1")
    try:
        cases = load_cases(read(args.cases))
        results = evaluate(cases, read(args.sources)["repositories"], load_replies(read(args.replies)))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    grouped: dict[str, list[Result]] = {"answerable": [], "requires_abstention": []}
    for case, result in zip(cases, results, strict=True):
        kind = "requires_abstention" if case.repository is None else "answerable"
        grouped[kind].append(result)

    totals = summarize(results)
    by_case_type = {name: summarize(group) for name, group in grouped.items()}
    if args.format == "text":
        for name, counts in {"overall": totals, **by_case_type}.items():
            print(f"{name}: {counts['correct']}/{counts['total']} correct, {counts['grounded']}/{counts['total']} grounded")
        for result in results:
            print(f"{result.id}: {result.reason}")
    else:
        print(json.dumps({
            **totals,
            "by_case_type": by_case_type,
            "results": [asdict(result) for result in results],
        }, indent=2))
    return int(totals["grounded"] / totals["total"] < args.min_grounded)


if __name__ == "__main__":
    raise SystemExit(main())
