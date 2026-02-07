"""YAML 配置加载，支持环境变量展开。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from common.exceptions import ConfigError

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)}")

_instance: dict[str, Any] | None = None

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


def _expand_env_vars(value: Any) -> Any:
    """递归展开字符串中的 ${ENV_VAR} 占位符。"""
    if isinstance(value, str):
        def _replacer(match: re.Match) -> str:
            env_key = match.group(1)
            env_val = os.environ.get(env_key)
            if env_val is None:
                return match.group(0)
            return env_val
        return _ENV_VAR_PATTERN.sub(_replacer, value)
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def load_settings(config_path: Path | None = None) -> dict[str, Any]:
    """加载并缓存 YAML 配置，支持环境变量展开。"""
    global _instance
    if _instance is not None:
        return _instance

    path = config_path or _DEFAULT_CONFIG_PATH
    if not path.exists():
        raise ConfigError(f"配置文件不存在: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"配置文件格式错误，期望字典: {path}")

    _instance = _expand_env_vars(raw)
    return _instance


def reset_settings() -> None:
    """重置配置缓存，用于测试。"""
    global _instance
    _instance = None
