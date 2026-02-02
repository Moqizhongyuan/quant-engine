"""
配置管理模块

提供配置加载、验证和访问功能。
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """数据库配置"""

    url: str = Field(default="sqlite:///data/quant_engine.db", description="数据库连接URL")
    echo: bool = Field(default=False, description="是否打印SQL语句")


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = Field(default="INFO", description="日志级别")
    format: Optional[str] = Field(None, description="日志格式")
    rotation: str = Field(default="10 MB", description="日志轮转大小")
    retention: str = Field(default="30 days", description="日志保留时间")
    path: Optional[str] = Field(None, description="日志文件路径")


class JoinQuantConfig(BaseModel):
    """聚宽配置"""

    enabled: bool = Field(default=True, description="是否启用")
    strategy_url: str = Field(default="", description="策略结果页面URL")
    username: str = Field(default="", description="用户名")
    password: str = Field(default="", description="密码")
    timeout: int = Field(default=30, description="请求超时秒数")
    max_retries: int = Field(default=3, description="最大重试次数")


class DataProviderConfig(BaseModel):
    """数据源配置"""

    joinquant: JoinQuantConfig = Field(default_factory=JoinQuantConfig)


class MiniQMTConfig(BaseModel):
    """miniQMT配置"""

    enabled: bool = Field(default=True, description="是否启用")
    path: str = Field(default="", description="QMT安装路径")
    account_id: str = Field(default="", description="账户ID")
    simulation: bool = Field(default=True, description="是否模拟交易")
    timeout: int = Field(default=10, description="连接超时秒数")


class BrokerConfig(BaseModel):
    """交易接口配置"""

    miniqmt: MiniQMTConfig = Field(default_factory=MiniQMTConfig)


class RiskConfig(BaseModel):
    """风控配置"""

    enabled: bool = Field(default=True, description="是否启用风控")
    max_position_ratio: float = Field(default=0.2, description="单只股票最大持仓比例")
    max_daily_loss_ratio: float = Field(default=0.05, description="单日最大亏损比例")
    stop_loss_ratio: float = Field(default=0.08, description="止损比例")
    take_profit_ratio: float = Field(default=0.20, description="止盈比例")
    max_holdings: int = Field(default=10, description="最大持仓股票数量")
    max_order_amount: float = Field(default=100000, description="单笔最大交易金额")


class TradingHoursConfig(BaseModel):
    """交易时间配置"""

    morning_start: str = Field(default="09:30", description="上午开始时间")
    morning_end: str = Field(default="11:30", description="上午结束时间")
    afternoon_start: str = Field(default="13:00", description="下午开始时间")
    afternoon_end: str = Field(default="15:00", description="下午结束时间")


class SchedulerConfig(BaseModel):
    """调度配置"""

    trading_hours: TradingHoursConfig = Field(default_factory=TradingHoursConfig)
    signal_fetch_time: str = Field(default="09:00", description="信号获取时间")
    order_execute_time: str = Field(default="09:35", description="订单执行时间")


class BacktestJoinQuantConfig(BaseModel):
    """聚宽回测配置"""

    enabled: bool = Field(default=False, description="是否启用")
    token: str = Field(default="", description="API Token")


class BacktestConfig(BaseModel):
    """回测配置"""

    joinquant: BacktestJoinQuantConfig = Field(default_factory=BacktestJoinQuantConfig)


class Settings(BaseSettings):
    """应用配置"""

    model_config = {"env_prefix": "QUANT_", "env_nested_delimiter": "__"}

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    data_provider: DataProviderConfig = Field(default_factory=DataProviderConfig)
    broker: BrokerConfig = Field(default_factory=BrokerConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)


def _expand_env_vars(config: dict) -> dict:
    """
    递归展开配置中的环境变量。

    Args:
        config: 配置字典

    Returns:
        展开后的配置字典
    """
    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = _expand_env_vars(value)
        elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            result[key] = os.environ.get(env_var, "")
        else:
            result[key] = value
    return result


def load_settings(config_path: Optional[str] = None) -> Settings:
    """
    加载配置文件。

    Args:
        config_path: 配置文件路径，默认为 config/settings.yaml

    Returns:
        Settings 实例

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 解析错误
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return Settings()

    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    config = _expand_env_vars(raw_config)
    return Settings(**config)


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    获取全局配置实例（单例模式）。

    Returns:
        Settings 实例
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reload_settings(config_path: Optional[str] = None) -> Settings:
    """
    重新加载配置。

    Args:
        config_path: 配置文件路径

    Returns:
        新的 Settings 实例
    """
    global _settings
    _settings = load_settings(config_path)
    return _settings
