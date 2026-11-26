"""Run a local, repeatable evaluation without calling a model."""

from argparse import ArgumentParser
from dataclasses import asdict
import json
from pathlib import Path

from .evaluate import evaluate, load_cases, load_replies


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("replies", type=Path, help="JSON array of model replies")
    parser.add_argument("--cases", type=Path, default=Path("fixtures/cases.json"))
    parser.add_argument("--sources", type=Path, default=Path("fixtures/repositories.json"))
    parser.add_argument("--min-grounded", type=float, default=0, help="Fail below this fraction (0 to 1)")
    args = parser.parse_args()
    if not 0 <= args.min_grounded <= 1:
        parser.error("--min-grounded must be between 0 and 1")
    try:
        results = evaluate(load_cases(read(args.cases)), read(args.sources)["repositories"], load_replies(read(args.replies)))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    correct = sum(result.correct for result in results)
    grounded = sum(result.grounded for result in results)
    print(json.dumps({
        "total": len(results),
        "correct": correct,
        "grounded": grounded,
        "results": [asdict(result) for result in results],
    }, indent=2))
    return int(grounded / len(results) < args.min_grounded)


if __name__ == "__main__":
    raise SystemExit(main())
