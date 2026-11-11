"""Dry run of a whole chair session, driven through hooks/hooks.json.

Every other test runs a script by path with `sys.executable`. This one
runs what Claude Code runs: the manifest's command string, through the
shell, with `${CLAUDE_PLUGIN_ROOT}` expanded, the PreToolUse matcher
applied to the tool name, and the manifest's own timeout. A hook that
only works when invoked "the test way" fails here.

Sandboxed like the rest of the suite (conftest.hook_env): temp files in
tmp_path, no metrics, no real tmux, no real settings.json.
"""
import json
import re
import subprocess

from conftest import REPO, hook_env

SESSION = "e2e-dry-run"


def _manifest():
    with open(REPO / "hooks" / "hooks.json", encoding="utf-8") as f:
        return json.load(f)["hooks"]


def fire(event, payload, tmp_path, **env):
    """Fire one event the way the harness does. Returns the parsed
    outputs of every hook that matched (empty output -> None)."""
    payload = {"session_id": SESSION, "hook_event_name": event, **payload}
    env = hook_env({"CLAUDE_PLUGIN_ROOT": str(REPO), **env}, tmp_path)
    outs = []
    for entry in _manifest()[event]:
        matcher = entry.get("matcher")
        if matcher and not re.search(matcher, payload.get("tool_name", "")):
            continue
        for hook in entry["hooks"]:
            proc = subprocess.run(
                ["/bin/sh", "-c", hook["command"]], input=json.dumps(payload),
                capture_output=True, text=True, env=env,
                timeout=hook["timeout"])
            assert proc.returncode == 0, proc.stderr
            out = proc.stdout.strip()
            outs.append(json.loads(out) if out else None)
    return outs


def context(outs):
    (out,) = outs
    return out["hookSpecificOutput"]["additionalContext"]


def decision(outs):
    (out,) = outs
    return out and out["hookSpecificOutput"]["permissionDecision"]


def tool(tool_name, **tool_input):
    return {"tool_name": tool_name, "tool_input": tool_input}


def test_a_fable_5_2_chair_session_end_to_end(tmp_path):
    start = fire("SessionStart",
                 {"source": "startup", "model": "claude-fable-5-2"}, tmp_path)
    assert "(FABLE profile)" in context(start)
    marker = tmp_path / f"fable-orch-model-{SESSION}.json"
    assert json.loads(marker.read_text())["profile"] == "fable"

    assert "You are the CHAIR" in context(
        fire("UserPromptSubmit", {"prompt": "refactor the parser"}, tmp_path))

    # The matcher keeps the guard off tools it does not gate.
    assert fire("PreToolUse", tool("Read", file_path="a.py"), tmp_path) == []

    # Two solo edits pass, the third draws the one deny, then quiet.
    assert decision(fire("PreToolUse", tool("Edit"), tmp_path)) is None
    assert decision(fire("PreToolUse", tool("Write"), tmp_path)) is None
    assert decision(fire("PreToolUse", tool("MultiEdit"), tmp_path)) == "deny"
    assert decision(fire("PreToolUse", tool("Edit"), tmp_path)) is None

    # A named spawn always passes.
    assert decision(fire("PreToolUse", tool(
        "Agent", name="impl", prompt="x" * 2000), tmp_path)) is None

    # The Fable limit runs dry; the chair resumes on Opus 5.5 and gets
    # only the switch delta, not a second core.
    switch = context(fire("SessionStart",
                          {"source": "resume", "model": "claude-opus-5-5"},
                          tmp_path))
    assert "Profile switch → OPUS chair" in switch
    assert "(OPUS profile)" not in switch

    solo = tmp_path / f"fable-orch-solo-{SESSION}.json"
    assert marker.is_file() and solo.is_file()
    assert fire("SessionEnd", {"reason": "exit"}, tmp_path) == [None]
    assert not marker.exists() and not solo.exists()


def test_an_unnamed_long_spawn_is_denied_once_end_to_end(tmp_path):
    long_brief = tool("Agent", prompt="x" * 2000)
    assert decision(fire("PreToolUse", long_brief, tmp_path)) == "deny"
    assert decision(fire("PreToolUse", long_brief, tmp_path)) is None
    # The denied spawn still counted as delegating: edits stay free.
    for _ in range(4):
        assert decision(fire("PreToolUse", tool("Edit"), tmp_path)) is None


def test_every_hook_stays_silent_when_switched_off(tmp_path):
    off = {"FABLE_ORCH_REMIND": "0", "FABLE_ORCH_SOLO_GUARD": "0"}
    assert fire("UserPromptSubmit", {"prompt": "hi"}, tmp_path, **off) == [None]
    for _ in range(4):
        assert decision(fire("PreToolUse", tool("Edit"), tmp_path, **off)) is None
