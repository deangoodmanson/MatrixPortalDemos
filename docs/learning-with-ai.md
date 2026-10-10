# Learning with AI — Claude Desktop & Claude Code

This project pairs well with AI assistants, but the goal is **AI as a tutor, not
an answer key.** That framing matters: the point of the exercises and the
heavily-commented `hs/` code is to build *your* understanding. Used well, an AI
assistant is a patient explainer and debugging partner. Used poorly, it short-
circuits the learning. (See [`how-this-was-built.md`](how-this-was-built.md) and
[`why-learn-to-code.md`](why-learn-to-code.md) for why that distinction is the
whole point.)

## Two editions, two coding philosophies

The two host editions are intentionally designed around different ways of
working — pick the one that matches your goal:

- **`pro/` — designed around agentic coding.** Its modular structure, type hints,
  tests, and config-as-deliverable exist so an AI agent (and a human reviewer)
  can extend it safely through prompts and configuration. It's the worked example
  of *directing* an agent to build production-quality software — the human is the
  architect and reviewer, the agent is the implementer. See
  [`how-this-was-built.md`](how-this-was-built.md).
- **`hs/` — designed around hands-on, interactive coding.** A single, linear,
  heavily-commented file you read, run, and modify yourself. The goal is for
  *you* to build the understanding, line by line.

These aren't walls. The `hs/` edition also **welcomes collaborative, AI-augmented
coding** — pairing with an assistant to explain, debug, and extend code you
understand. Tools that fit this model include:

- **[Anthropic Claude Code](https://www.anthropic.com/claude-code)** and Claude Desktop
- **[Microsoft / GitHub Copilot](https://github.com/features/copilot)**
- **[Google Antigravity](https://antigravity.google/)**

The principle is the same across all of them and is the heart of this guide:
**use AI as a collaborator and tutor, not an answer key.** Augmented coding means
*you* stay the author — the assistant accelerates work you can still read,
explain, and defend.

> This guide's examples use Anthropic's Claude tools because that's what the
> project was built with, but the habits transfer directly to Copilot,
> Antigravity, or any other assistant.

---

## Two tools, two roles (Claude)

- **Claude Desktop** — the chat app. Great for conceptual Q&A, lesson planning,
  and explaining code or errors you paste in. It does **not** see your files
  unless you connect a filesystem tool.
- **Claude Code** — runs in your terminal inside the project. It can read, run,
  and modify the actual code. Powerful for guided walkthroughs and debugging —
  and exactly why students should point it at a **copy** they can't break.

---

## For Teachers

### Claude Desktop (planning & assessment)
- Paste `hs/src/config.py` and the top of `hs/src/camera_feed.py`:
  *"Write a 50-minute lesson plan with learning objectives and five
  check-for-understanding questions for high-school beginners."*
- *"Generate three more exercises like the ones in `hs/README.md`, at easy /
  medium / hard difficulty, with answer keys for me only."*
- Build a quiz or rubric from the "Key Concepts Covered" list (RGB565, serial
  communication, loops, functions).
- *"Map this project's concepts to CSTA / AP CS Principles standards."*

### Claude Code (lab prep & support)
- Pre-flight a lab: `claude` in the repo →
  *"Run the HS version headless and tell me exactly what students will see, and
  the three most likely things to go wrong on classroom laptops."*
- Environment setup across machines: it can run `uv sync`, diagnose a missing
  camera, or apply the Linux `dialout` group fix.
- Paste a student's modified file: *"Give encouraging, specific feedback. Point
  at what to investigate — don't rewrite it for them."*

---

## For Students

### Claude Desktop (understand, don't outsource)
- Paste an error message **and** the code around it:
  *"Explain this error in plain English. Give me a hint, not the fix."*
- Concept questions straight from the code:
  *"In `convert_to_rgb565`, why is green divided by 4 but red and blue by 8?"*
  (That's literally Exercise 3 — try it yourself first.)
- *"What does RGB565 mean, and why not just use full color?"*

### Claude Code (a guided walkthrough)
- *"Explain `camera_feed.py` from the top, section by section, like I'm new to
  Python."*
- *"Walk me through what happens, step by step, when I press the `b` key."*
- Socratic debugging: *"I set `MATRIX_WIDTH = 32` and the image looks squished.
  Ask me questions to help me figure out why — don't just tell me."*

### Good habits
- Work on a **copy**, so experiments (and the AI's suggestions) can't break the
  original.
- Use the exercises in `hs/README.md` with the AI as a **hint-giver**: try
  first, ask for a nudge, only then ask for the answer — and make sure you can
  explain it afterward.
- If the AI writes something you don't understand, that's a stop sign: ask it
  to explain until you do. Code you can't explain isn't yours yet.

---

## Caveats & setup notes

- **Claude Desktop** can't read your local files unless you wire up the
  filesystem connector (MCP). Pasting code/errors into the chat is the simplest
  path for most classroom use.
- **Claude Code** has full read/write/run access to whatever folder you launch
  it in. For students, launch it in a throwaway copy of the project, not the
  graded original.
- The camera can only be used by one program at a time — close Zoom/FaceTime
  and any debugger sessions before running the feed.
