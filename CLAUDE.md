# ForenSight — instructions for Claude

1. **Read `MEMORY.md` at the start of every session.** It holds the goals, design
   decisions, Docker setup and the full history log.
2. **At the end of every session, append an entry to `MEMORY.md` → "History Log"**
   (date, what was done, why, open issues, next step). If a design decision changes,
   update the relevant section *and* note the change in the log — never silently rewrite history.
3. Everything runs in Docker (`docker compose up --build`). Don't add host-only setup steps.
4. Never run ML training yourself — write the code and give the user the command to run.
5. Never `git commit` / push; the user commits manually. No Claude attribution lines.
6. The project name is **ForenSight** (the proposal's "TruthLens" mentions are outdated).
7. **Comments must be simple and basic** — short plain-English sentences that any developer
   can understand. Explain what a block does and why; explain technical terms (e.g. "z-score",
   "FFT") in a few words the first time they appear in a file.
