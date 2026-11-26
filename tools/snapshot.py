"""Fetch public GitHub repository metadata for the evaluation fixtures."""

from argparse import ArgumentParser
import json
from pathlib import Path
from urllib.request import Request, urlopen

REPOSITORIES = ("spring-projects/spring-boot", "nestjs/nest", "fastapi/fastapi", "microsoft/playwright")


def fetch(name: str) -> dict[str, str]:
    url = f"https://api.github.com/repos/{name}"
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "github-grounding-eval"})
    with urlopen(request, timeout=15) as response:
        body = json.load(response)
    return {
        "url": body["html_url"],
        "language": body["language"],
        "license": body["license"]["spdx_id"],
    }


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("fixtures/repositories.json"))
    args = parser.parse_args()
    snapshot = {"repositories": {name: fetch(name) for name in REPOSITORIES}}
    args.output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
