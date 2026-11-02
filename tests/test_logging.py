import json

from ali_tool.core import logging as ali_logging


def test_commands_log_rotates_without_losing_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(ali_logging, "COMMAND_LOG_MAX_BYTES", 1_000)
    monkeypatch.setattr(ali_logging, "COMMAND_LOG_BACKUPS", 50)

    logger = ali_logging.ALILogger()
    for i in range(40):
        logger.log_command(f"SPLIT {i}", result="tmux split-window")

    log_dir = tmp_path / ".local/share/ali/logs"
    files = sorted(log_dir.glob("commands.jsonl*"))
    assert len(files) > 1
    lines = [ln for f in files for ln in f.read_text().splitlines()]
    assert sorted(json.loads(ln)["command_raw"] for ln in lines) == sorted(
        f"SPLIT {i}" for i in range(40)
    )


def test_commands_log_is_not_duplicated_across_loggers(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    ali_logging.ALILogger().log_command("GO .1")
    ali_logging.ALILogger().log_command("GO .2")

    path = tmp_path / ".local/share/ali/logs/commands.jsonl"
    assert [json.loads(ln)["command_raw"] for ln in path.read_text().splitlines()] == [
        "GO .1",
        "GO .2",
    ]
