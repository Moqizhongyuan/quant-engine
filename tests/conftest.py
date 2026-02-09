"""共享 fixtures：mock easytrader 模块、样本数据、配置重置。"""

from __future__ import annotations

import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from common.config import reset_settings


@pytest.fixture(autouse=True)
def _reset_config():
    """每个测试前后重置配置缓存，保证测试隔离。"""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture()
def mock_easytrader_module():
    """Mock easytrader 模块，拦截延迟导入。"""
    mock_module = MagicMock()
    with patch.dict(sys.modules, {"easytrader": mock_module}):
        yield mock_module


@pytest.fixture()
def mock_client():
    """easytrader 客户端 mock 对象。"""
    client = MagicMock()
    client.buy.return_value = {"entrust_no": "BUY001"}
    client.sell.return_value = {"entrust_no": "SELL001"}
    client.cancel_entrust.return_value = None
    return client


@pytest.fixture()
def connected_broker(mock_easytrader_module, mock_client):
    """已连接的 EasyTraderBroker 实例。"""
    mock_easytrader_module.use.return_value = mock_client
    from trading.easytrader_broker import EasyTraderBroker

    broker = EasyTraderBroker(
        broker_name="ht",
        account="test_account",
        password="test_password",
    )
    broker.connect()
    return broker


@pytest.fixture()
def sample_settings_easytrader():
    """EasyTrader 配置字典。"""
    return {
        "broker": {
            "active": "easytrader",
            "easytrader": {
                "broker_name": "ht",
                "account": "test_account",
                "password": "test_password",
                "exe_path": "",
            },
        },
    }


@pytest.fixture()
def sample_settings_qmt():
    """QMT 配置字典。"""
    return {
        "broker": {
            "active": "qmt",
            "qmt": {
                "path": "/opt/qmt",
                "account_id": "qmt_001",
            },
        },
    }


@pytest.fixture()
def sample_chinese_position():
    """easytrader 原始中文字段持仓数据。"""
    return [
        {
            "证券代码": "000001",
            "证券名称": "平安银行",
            "股票余额": 1000,
            "可用余额": 800,
            "成本价": 12.50,
            "市价": 13.20,
            "市值": 13200.00,
            "盈亏": 700.00,
            "盈亏比例(%)": 5.60,
        },
    ]


@pytest.fixture()
def sample_chinese_balance():
    """easytrader 原始中文字段资金数据。"""
    return {
        "总资产": 100000.00,
        "可用金额": 50000.00,
        "股票市值": 48000.00,
        "冻结金额": 2000.00,
    }


@pytest.fixture()
def sample_chinese_orders():
    """easytrader 原始中文字段委托数据。"""
    return [
        {
            "合同编号": "ORD001",
            "证券代码": "000001",
            "操作": "买入",
            "委托数量": 500,
            "委托价格": 12.80,
            "成交数量": 300,
            "成交均价": 12.75,
            "备注": "部成",
        },
        {
            "合同编号": "ORD002",
            "证券代码": "600036",
            "操作": "卖出",
            "委托数量": 200,
            "委托价格": 35.50,
            "成交数量": 200,
            "成交均价": 35.50,
            "备注": "已成",
        },
    ]
