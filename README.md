# GitHub Grounding Eval

A small, offline evaluation harness for structured answers about public GitHub repositories. It scores a correct answer and a source-backed answer separately, so a model does not get evidence credit for citing the wrong project.

## Run it

Python 3.12 and its standard library are enough.

~~~text
python -m grounding_eval examples/replies.json
python -m unittest discover -s tests -v
~~~

The included example has 7 answers, 6 correct answers, and 5 grounded answers. One example cites an unrelated repository and one gives the wrong license. The last two questions exercise abstention when a fact is absent from the snapshot. The JSON report includes separate counts for answerable cases and cases that require abstention.

To gate a run in CI, add --min-grounded followed by a fraction between 0 and 1. For example, a threshold of 0.8 fails the supplied example.

## Reply format

~~~json
{"id": "spring-language", "answer": "Java", "citations": ["spring-projects/spring-boot"]}
~~~

The CLI expects a JSON array of replies. Use a null answer with no citations when the available sources cannot answer a question. Answer matching ignores case and repeated whitespace. The evaluator checks structured facts and deliberately avoids subjective or free-form grading.

## Data provenance

The snapshot contains the public repository URL, primary language, and SPDX license shown by the GitHub repository metadata API. The questions and example replies were written for this project. Refresh the snapshot with the following command.

~~~text
python tools/snapshot.py
~~~

- [Spring Boot](https://github.com/spring-projects/spring-boot)
- [NestJS](https://github.com/nestjs/nest)
- [FastAPI](https://github.com/fastapi/fastapi)
- [Playwright](https://github.com/microsoft/playwright)
- [GitHub repository metadata API](https://docs.github.com/en/rest/repos/repos#get-a-repository)

Independent portfolio project, built with AI assistance. The evaluation and tests run locally without a model API or a GitHub token.

### Terminal report

Use `--format text` for a terminal summary of case counts and results. The default is JSON.

`--min-abstention FRACTION` independently checks the grounded rate for cases requiring abstention. A positive threshold requires at least one such case.

Both report formats include `source_sha256`, the SHA-256 of the exact evidence snapshot file used to evaluate replies.

`cases_sha256` and `replies_sha256` identify the exact case and reply files used for a run.

Use `--output report.json` or `--format text --output report.txt` to store a report in a new file. Reports are saved even when a threshold fails.

`--require-all-replies` returns status 1 when a case has no reply. A reply with a null answer still counts as a supplied reply.
