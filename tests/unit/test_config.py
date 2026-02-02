"""
配置模块单元测试
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from quant_engine.utils.config import (
    Settings,
    load_settings,
    _expand_env_vars,
)


class TestConfig:
    """配置模块测试"""

    def test_default_settings(self):
        """测试默认配置"""
        settings = Settings()

        assert settings.database.url == "sqlite:///data/quant_engine.db"
        assert settings.risk.enabled is True
        assert settings.risk.max_position_ratio == 0.2

    def test_load_settings_from_file(self):
        """测试从文件加载配置"""
        config_content = {
            "database": {
                "url": "sqlite:///test.db",
                "echo": True,
            },
            "risk": {
                "enabled": False,
                "max_position_ratio": 0.3,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_content, f)
            config_path = f.name

        try:
            settings = load_settings(config_path)

            assert settings.database.url == "sqlite:///test.db"
            assert settings.database.echo is True
            assert settings.risk.enabled is False
            assert settings.risk.max_position_ratio == 0.3
        finally:
            os.unlink(config_path)

    def test_expand_env_vars(self):
        """测试环境变量展开"""
        os.environ["TEST_VAR"] = "test_value"

        config = {
            "key1": "${TEST_VAR}",
            "key2": "normal_value",
            "nested": {
                "key3": "${TEST_VAR}",
            },
        }

        result = _expand_env_vars(config)

        assert result["key1"] == "test_value"
        assert result["key2"] == "normal_value"
        assert result["nested"]["key3"] == "test_value"

        del os.environ["TEST_VAR"]

    def test_expand_missing_env_var(self):
        """测试缺失的环境变量"""
        config = {
            "key": "${MISSING_VAR}",
        }

        result = _expand_env_vars(config)
        assert result["key"] == ""

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        settings = load_settings("/nonexistent/path/config.yaml")
        assert settings is not None
        assert settings.database.url == "sqlite:///data/quant_engine.db"
