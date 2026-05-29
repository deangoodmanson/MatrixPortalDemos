# How This Project Was Built — An Agentic Coding Experiment

This repository is, in addition to being a working LED-matrix project, a
deliberate experiment in **agentic coding**: building real software primarily
through **prompts and configuration**, with an AI coding agent (Claude Code)
doing the actual typing.

It's shared openly because the "how" is as instructive for students and
teachers as the "what" — especially alongside [`why-learn-to-code.md`](why-learn-to-code.md),
which asks the honest question *"If AI generated this, why learn Python?"*

## The division of labor

| The human (director) | The agent (implementer) |
|----------------------|-------------------------|
| Chooses the stack: `uv`, `ruff`, `ty`, CircuitPython, OpenCV, Pillow | Writes all the code, across three editions |
| Sets standards (types, tests, docs, style) | Writes and runs the tests, fixes its own bugs |
| Reviews, redirects, and decides trade-offs | Runs the CI gate, lint, type-checks before pushing |
| Steers entirely via prompts and config | Manages branches, PRs, and git hygiene |

The human author is fluent in Python and gives specific library and tooling
direction — but **deliberately does not hand-edit the code**. If something is
wrong, it's fixed by a better prompt or a clearer standard, not a manual patch.
That constraint is the whole point: it tests how far prompt- and
config-driven development can actually go.

## What that approach produced

- Three coordinated editions from one set of intentions: a heavily-commented
  high-school version (`hs/`), a typed/tested production version (`pro/`), and
  CircuitPython firmware (`matrix-portal/`).
- A 220+ test suite, type checking with `ty`, linting/formatting with `ruff`.
- A CI gate mirrored locally as `make ci` in each package, so "green locally"
  means "green in CI."
- Configuration treated as a first-class deliverable: YAML configs, CLI flags,
  a runtime keyboard toggle, and per-platform behavior.

## What it honestly took (the un-hyped parts)

Agentic coding is not "type a wish, get perfect software." The things that
actually made it work are the same things that make *human* teams work:

- **Small, verifiable steps.** Each change is run, tested, and type-checked
  before moving on.
- **Catching environment-specific bugs.** Example: a printing change passed on
  macOS but crashed CI on Linux because `lpr` wasn't installed — the kind of
  bug that only direction, review, and real CI surface, not the first draft.
- **Fighting drift.** Hardcoded test counts and stale docs creep in; keeping
  them honest is ongoing work (this very doc lives on a docs-cleanup branch).
- **Knowing what "good" looks like.** The agent proposes; the human still has
  to recognize a fragile fix, an altitude problem, or a missing test.

## Why this matters for the classroom

This is a concrete answer to *"why learn to code if AI can do it?"*: the value
moved up a level, not away. You still need to **direct, evaluate, debug, and
know what good looks like** — and you can't do any of that well without
understanding the code. The agent is a fast, tireless implementer; the human is
the architect, reviewer, and final judge.

For ways to use AI tools as a *tutor* (not an answer key) while learning this
project, see [`learning-with-ai.md`](learning-with-ai.md).
