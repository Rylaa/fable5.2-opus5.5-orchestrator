# Fable Orchestrator

[![CI](https://github.com/Rylaa/fable5.2-opus5.5-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/Rylaa/fable5.2-opus5.5-orchestrator/actions/workflows/ci.yml)

**Run Claude Fable 5.2 all day — without watching the usage meter.**

Fable 5.2 is the best chair a Claude Code session can have, and the most expensive one. This plugin keeps it on planning and decisions and sends the work to named workers: the volume to **Sonnet 5.5**, the hard slices (architecture, irreversible migrations, security review) straight to **Opus 5.5**. No tier ever runs above `high` effort.

## The division of labor

```
                        ┌─────────────────────────────────┐
                        │        FABLE 5.2 — chair        │
                        │    plan · arbitrate · decide    │
                        │  sizes tier + effort per task   │
                        └────────────────┬────────────────┘
                                         │
                    specs down           │           briefs up
                                         │
           ┌────────────────────────┬────┴───────────────────┬────────────────────────┐
           ▼                        ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│SONNET 5.5 · low–med │  │SONNET 5.5 · med–high│  │SONNET 5.5 · med–high│  │   OPUS 5.5 · high   │
│   mechanical bulk   │  │   implementation    │  │   routine judgment  │  │  hard work · direct │
│   grep·fetch·scan   │  │   code · tests      │  │   briefs · review   │  │  architecture       │
│   format · read     │  │   debug · refactor  │  │   filtering         │  │  migrations·security│
└─────────────────────┘  └─────────────────────┘  └──────────┬──────────┘  └──────────┬──────────┘
                                                             │ uncertain /            │ beyond
                                                             │ high stakes            │ opus
                                                          ┌──▼────────────────────────▼──┐
                                                          │   escalation · one way only  │
                                                          │ OPUS 5.5 → FABLE 5.2 → stop  │
                                                          └──────────────────────────────┘
```

- **Escalation is one-way.** When `high` is not enough, the work moves up a tier, not up in effort. Sonnet's "uncertain" goes to Opus, never back to the chair.
- **A declined task is re-run unchanged** on another tier, never reworded. If that tier declines too, the chair stops and tells you.

## What the plugin does

**1 · The chair profile.** Every session starts with a ~3.7k-char core: delegate by default, hand off through `./.workflow/scratch/`, name the workers, set `model` and effort per spawn. The detail is in the `orchestrator:playbook` skill, loaded before the first delegation. Worker reports are capped at 40 lines; longer material goes to disk.

**2 · The solo guard.** The chair's own `Edit` / `Write` / `MultiEdit` / `NotebookEdit` calls are counted. The 3rd one in a session that has spawned no worker is denied once, then the guard stays quiet. One spawned worker disarms it. A fork does not count as a worker.

**3 · The naming gate.** The first unnamed spawn with a 1500+ char prompt is denied once. Named workers run in tmux panes you can watch; unnamed ones are invisible until they return.

**4 · The per-prompt reminder.** One line rides every prompt: *You are the CHAIR. Delegate by default.*

Workers (teammates) get none of this — the rules are for the chair. When a session ends, its teammate panes are killed.

## Two chairs

Fable is primary. When its limit runs out, move the chair to Opus — the Opus profile keeps the same rules with the fable tier resting:

```
claude --continue --model opus
```

Do not use `/model` for this: it is invisible to hooks, so the session keeps the Fable profile. Run `/compact` on the new chair if the history is long.

## Install

```
/plugin marketplace add Rylaa/fable5.2-opus5.5-orchestrator
/plugin install orchestrator@fable-orchestrator
```

Restart Claude Code afterwards — hooks load when the CLI starts.

- Run the chair at `/effort medium`, `high` for the hardest planning.
- Recommended: set `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` under `"env"`, so a spawn that forgets `model` does not run on Fable.
- Requires `python3` 3.10+ and macOS or Linux (the hooks use `ps` and `tmux`).

To watch the team, start `claude` inside tmux; the workers appear as panes in your window.

<details>
<summary>Manual install (without the plugin system)</summary>

1. Copy `scripts/*.py` (except `stats.py`) to `~/.claude/hooks/`.
2. Merge into `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/inject_instructions.py", "timeout": 10 } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/remind_chair.py", "timeout": 10 } ] }
    ],
    "PreToolUse": [
      {
        "matcher": "^(Agent|Task|Edit|Write|MultiEdit|NotebookEdit)$",
        "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/solo_guard.py", "timeout": 10 } ]
      }
    ],
    "SessionEnd": [
      { "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/cleanup_session_cache.py", "timeout": 20 } ] }
    ]
  }
}
```

3. Append `instructions/dynamic-workflow-fable.md` to `~/.claude/CLAUDE.md` and copy the playbook to `~/.claude/skills/playbook/SKILL.md`.

Don't run the plugin and the manual install together — every hook would fire twice.

</details>

## Configuration

Optional, in `~/.claude/settings.json` under `"env"`:

```
┌───────────────────────────────┬─────────┬────────────────────────────────────────────┐
│ Env var                       │ Default │ Meaning                                    │
├───────────────────────────────┼─────────┼────────────────────────────────────────────┤
│ FABLE_ORCH_SOLO_EDITS         │ 3       │ deny at the Nth chair edit; 0 disables     │
│ FABLE_ORCH_NAME_CHARS         │ 1500    │ spawn prompt size that needs a name; 0 off │
│ FABLE_ORCH_SOLO_GUARD         │ (on)    │ 0 disables the solo gate entirely          │
│ FABLE_ORCH_REMIND             │ (on)    │ 0 disables the per-prompt line             │
│ FABLE_ORCH_PROFILE            │ auto    │ pin the chair profile: auto | fable | opus │
│ FABLE_ORCH_TEAMMATE_INJECT    │ (off)   │ 1 injects the profile into teammates too   │
│ FABLE_ORCH_METRICS            │ (on)    │ 0 disables local metrics logging           │
│ FABLE_ORCH_SWARM_CLEANUP      │ (on)    │ 0 disables all teammate reaping            │
│ FABLE_ORCH_SWARM_MAX_IDLE_H   │ 48      │ sweep swarms idle ≥ N hours; 0 disables    │
└───────────────────────────────┴─────────┴────────────────────────────────────────────┘
```

The profile is picked from, first match wins: `FABLE_ORCH_PROFILE`, the `--model` flag the session was launched with, `model` in `settings.json`. Any model that is not Opus gets the Fable profile.

Metrics (events only, never prompt content) go to `~/.claude/fable-orch/metrics.jsonl`; `python3 scripts/stats.py` prints a summary.

## Upgrading to v0.17.2

- Effort is capped at `high` for every tier; `xhigh` and `max` are gone.
- The chair is detected from the `--model` launch flag. Move the chair by relaunching, not with `/model`.
- Every spawn must set `model`.
- Python 3.10+ is required.

## Tests

```
python3 -m pytest tests/ -q
```

The hooks run as real subprocesses. `tests/test_e2e_dry_run.py` replays a whole session through `hooks/hooks.json`, as Claude Code runs it.

## Limitations

- **The solo guard counts edits, not work.** A chair that writes files through `Bash` never trips it.
- **Each gate fires once per session.** A chair can ignore the nudge and carry on.
- **`/model` is invisible to the hooks.** Relaunch with `--model`, or pin `FABLE_ORCH_PROFILE`.

## License

MIT
