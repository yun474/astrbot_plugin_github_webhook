"""Check schema defaults and upgrades from old configuration files."""

import json
from pathlib import Path

import pytest
from astrbot.api import AstrBotConfig

from src.core.config import PluginConfig


def test_old_configuration_uses_new_default():
    config = PluginConfig({"target_umo": "test:GroupMessage:openid"})
    assert config.push_mode == "Markdown 推送"
    assert config.qq_mention_openid == ""
    assert config.llm_timeout_fallback_md is True
    assert config.rate_limit == 10


def test_real_astrbot_config(tmp_path):
    schema = json.loads(
        (Path(__file__).parents[1] / "_conf_schema.json").read_text("utf-8")
    )
    config = AstrBotConfig(str(tmp_path / "config.json"), schema=schema)
    config["target_umo"] = "official:FriendMessage:user-openid"
    config["push_mode"] = "原生文本"
    result = PluginConfig(config)
    assert result.target_umo == "official:FriendMessage:user-openid"
    assert result.push_mode == "原生文本"


def test_mention_openid_is_trimmed():
    assert (
        PluginConfig({"qq_mention_openid": "  member_123  "}).qq_mention_openid
        == "member_123"
    )


@pytest.mark.parametrize("openid", ['<qqbot-at-user id="x" />', 'x" /><evil>', "x\ny"])
def test_mention_rejects_tags_and_attribute_injection(openid):
    with pytest.raises(ValueError, match="qq_mention_openid"):
        PluginConfig({"qq_mention_openid": openid})


@pytest.mark.parametrize(
    "config",
    [
        {"target_umo": "123456"},
        {"target_umo": "test:GroupMessage:"},
        {"port": 65536},
        {"agent_timeout": 0},
        {"rate_limit": -1},
    ],
)
def test_bad_configuration(config):
    with pytest.raises(ValueError):
        PluginConfig(config)


def test_schema_exposes_one_mode_selector_and_separate_timeout_switch():
    schema = json.loads(
        (Path(__file__).parents[1] / "_conf_schema.json").read_text("utf-8")
    )
    assert schema["push_mode"]["options"] == ["原生文本", "Markdown 推送", "LLM 改写"]
    assert schema["llm_timeout_fallback_md"]["type"] == "bool"
    assert "enable_agent" not in schema
    assert "qq_official_markdown" not in schema


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="push_mode"):
        PluginConfig({"push_mode": "both"})
