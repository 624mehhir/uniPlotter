# CLAUDE.md

## Current state

M1 complete: health check, shared schema, drawing function.
Next milestone: M2 (COCO parser + /plot endpoint).

Update this line at the end of every session. Use it to identify which milestone section in MILESTONES.md is "current".

This file is read at the start of every session. Also read `PRD.md` and
`ARCHITECTURE.md` once per session before writing any code. Then read ONLY
the current milestone's section in `MILESTONES.md` — do not read or act on
other milestones' scope, even if you can see them in the same file.

## Golden rule

Implement exactly what the current milestone asks for. Nothing more.
If you think something extra would "obviously be needed later," do not add
it now — flag it in your response as a note instead, and wait to be asked.

## Explicit forbidden list — do NOT do these unless a milestone explicitly asks

- Do not implement format auto-detection. The format is always explicitly
  provided by the user/caller.
- Do not add a database, ORM, or any persistent storage.
- Do not add user accounts, auth, sessions, or API keys.
- Do not add Docker, docker-compose, or any deployment config.
- Do not add a frontend framework (React, Vue, etc.) — plain HTML/CSS/JS only,
  and only when a milestone specifically asks for the frontend.
- Do not add logging frameworks, monitoring, or telemetry.
- Do not add automated tests unless the milestone explicitly asks for them.
- Do not add batch/multi-image upload support.
- Do not implement brush/mask-based annotation rendering — that's a future
  version, not part of any current milestone unless stated.
- Do not add retry logic, caching, or rate limiting.
- Do not add dependencies beyond what a milestone explicitly requires.
- Do not write speculative code for formats or features not in the current
  milestone, even as commented-out stubs.
- Do not add extensive docstrings/comments explaining self-evident code.
  Comment only non-obvious decisions (e.g., a coordinate conversion formula).
  - Do not use Python's built-in `hash()` for label→colour mapping. It is salted
  per process, so the same label would get a different colour on every server
  restart. `draw.py` uses a hashlib digest deliberately — keep it.
- Do not change the `/plot` response shape defined in ARCHITECTURE.md, or the
  parser return contract, once M2 has implemented them.
- Do not add per-format parameters, per-format branches, or per-format helper
  functions to `draw.py`. It sees only the shared schema.

## Architecture rule (non-negotiable, applies to every milestone)

Every format parser must output the shared annotation schema defined in
`ARCHITECTURE.md`. There must be exactly ONE drawing function used by all
formats. If implementing a new parser seems to require changing the drawing
function's behavior, stop and flag this rather than writing a
format-specific drawing path.

## Before finishing a session

1. Confirm the server still starts, from the repo root, with no errors:
   `uvicorn app.main:app --reload`
2. Confirm existing/previously-working endpoints and formats still work —
   do not regress prior milestones' work.
3. Summarize, in plain language, exactly what was added this session and
   which milestone it corresponds to. Do not summarize the whole project.
