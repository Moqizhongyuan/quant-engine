"""Broker 工厂，根据配置创建对应的券商适配器实例。"""

from __future__ import annotations

from typing import Any

from common.exceptions import ConfigError
from common.types import BrokerType
from trading.broker import Broker
from trading.easytrader_broker import EasyTraderBroker
from trading.qmt_broker import QMTBroker


def create_broker(settings: dict[str, Any]) -> Broker:
    """根据配置字典创建 Broker 实例。"""
    broker_cfg = settings.get("broker")
    if not broker_cfg:
        raise ConfigError("配置中缺少 broker 节")

    active = broker_cfg.get("active", "")
    try:
        broker_type = BrokerType(active)
    except ValueError:
        raise ConfigError(f"不支持的 broker 类型: {active}")

    if broker_type == BrokerType.EASYTRADER:
        et_cfg = broker_cfg.get("easytrader", {})
        return EasyTraderBroker(
            broker_name=et_cfg.get("broker_name", "ht"),
            account=et_cfg.get("account", ""),
            password=et_cfg.get("password", ""),
            exe_path=et_cfg.get("exe_path", ""),
        )

    if broker_type == BrokerType.QMT:
        qmt_cfg = broker_cfg.get("qmt", {})
        return QMTBroker(
            path=qmt_cfg.get("path", ""),
            account_id=qmt_cfg.get("account_id", ""),
        )

    raise ConfigError(f"未处理的 broker 类型: {active}")
