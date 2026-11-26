"""Evaluate answer accuracy and evidence support independently."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Case:
    id: str
    prompt: str
    repository: str | None
    field: str | None


@dataclass(frozen=True)
class Reply:
    id: str
    answer: str | None
    citations: tuple[str, ...]


@dataclass(frozen=True)
class Result:
    id: str
    correct: bool
    grounded: bool
    reason: str


def normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def load_cases(raw: list[dict[str, Any]]) -> list[Case]:
    cases = [Case(**item) for item in raw]
    if not cases:
        raise ValueError("The case file must contain at least one case")
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Duplicate case ID")
    for case in cases:
        if bool(case.repository) != bool(case.field):
            raise ValueError(f"{case.id}: provide both repository and field, or neither")
    return cases


def load_replies(raw: list[dict[str, Any]]) -> dict[str, Reply]:
    replies = {}
    for item in raw:
        case_id, answer, citations = item["id"], item["answer"], item["citations"]
        if not isinstance(case_id, str) or (answer is not None and not isinstance(answer, str)):
            raise ValueError("Reply IDs and non-null answers must be strings")
        if not isinstance(citations, list) or any(not isinstance(ref, str) for ref in citations):
            raise ValueError(f"{case_id}: citations must be an array of repository names")
        if case_id in replies:
            raise ValueError(f"Duplicate reply ID: {case_id}")
        replies[case_id] = Reply(case_id, answer, tuple(citations))
    return replies


def evaluate(cases: list[Case], repositories: dict[str, Any], replies: dict[str, Reply]) -> list[Result]:
    extras = set(replies).difference(case.id for case in cases)
    if extras:
        raise ValueError("Replies have unknown case IDs: " + ", ".join(sorted(extras)))
    results = []
    for case in cases:
        expected = None
        if case.repository is not None:
            source = repositories.get(case.repository, {})
            expected = source.get(case.field)
            if not isinstance(expected, str) or not expected:
                raise ValueError(f"{case.id}: missing snapshot evidence for {case.repository}/{case.field}")

        reply = replies.get(case.id)
        if reply is None:
            result = Result(case.id, False, False, "Missing reply")
        elif expected is None:
            abstained = reply.answer is None
            grounded = abstained and not reply.citations
            reason = "Correct abstention" if grounded else "The snapshot cannot answer this question"
            result = Result(case.id, abstained, grounded, reason)
        else:
            correct = reply.answer is not None and normalize(reply.answer) == normalize(expected)
            cited = set(reply.citations) == {case.repository}
            if not correct:
                reason = "Answer differs from the snapshot"
            elif not cited:
                reason = "Cite the repository that provides this field"
            else:
                reason = "Supported by the snapshot"
            result = Result(case.id, correct, correct and cited, reason)
        results.append(result)
    return results
