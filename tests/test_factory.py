"""create_broker 工厂函数测试。"""

from __future__ import annotations

import pytest

from common.exceptions import ConfigError
from trading.easytrader_broker import EasyTraderBroker
from trading.factory import create_broker
from trading.qmt_broker import QMTBroker


class TestCreateBrokerEasytrader:
    """测试创建 EasyTraderBroker。"""

    def test_create_easytrader_broker(self, sample_settings_easytrader):
        """正常创建 EasyTraderBroker 实例。"""
        broker = create_broker(sample_settings_easytrader)
        assert isinstance(broker, EasyTraderBroker)

    def test_easytrader_default_values(self):
        """缺少子配置时使用默认值。"""
        settings = {"broker": {"active": "easytrader"}}
        broker = create_broker(settings)
        assert isinstance(broker, EasyTraderBroker)
        assert broker._broker_name == "ht"
        assert broker._account == ""
        assert broker._password == ""
        assert broker._exe_path == ""


class TestCreateBrokerQMT:
    """测试创建 QMTBroker。"""

    def test_create_qmt_broker(self, sample_settings_qmt):
        """正常创建 QMTBroker 实例。"""
        broker = create_broker(sample_settings_qmt)
        assert isinstance(broker, QMTBroker)

    def test_qmt_default_values(self):
        """缺少子配置时使用默认值。"""
        settings = {"broker": {"active": "qmt"}}
        broker = create_broker(settings)
        assert isinstance(broker, QMTBroker)


class TestCreateBrokerErrors:
    """测试工厂函数错误处理。"""

    def test_missing_broker_config(self):
        """缺少 broker 配置节抛出 ConfigError。"""
        with pytest.raises(ConfigError, match="缺少 broker 节"):
            create_broker({})

    def test_invalid_active_value(self):
        """无效的 active 值抛出 ConfigError。"""
        settings = {"broker": {"active": "unknown"}}
        with pytest.raises(ConfigError, match="不支持的 broker 类型"):
            create_broker(settings)

    def test_empty_active_value(self):
        """空的 active 值抛出 ConfigError。"""
        settings = {"broker": {"active": ""}}
        with pytest.raises(ConfigError, match="不支持的 broker 类型"):
            create_broker(settings)
