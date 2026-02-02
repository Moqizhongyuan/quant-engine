"""
回测接口适配器基类

定义回测接口的抽象接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class BacktestResult:
    """回测结果"""

    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal
    total_return: Decimal
    annual_return: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    win_rate: Decimal
    trade_count: int
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class StrategyMetrics:
    """策略指标"""

    total_return: Decimal
    annual_return: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    win_rate: Decimal
    profit_loss_ratio: Decimal
    avg_holding_days: float
    trade_count: int
    daily_returns: Optional[List[Decimal]] = None


class BacktestProvider(ABC):
    """
    回测接口抽象基类。

    所有回测接口适配器必须实现此接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """接口名称"""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """是否已连接"""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        建立连接。

        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def run_backtest(
        self,
        strategy_code: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: Decimal = Decimal("1000000"),
        params: Optional[Dict[str, Any]] = None,
    ) -> BacktestResult:
        """
        运行回测。

        Args:
            strategy_code: 策略代码
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            params: 策略参数

        Returns:
            回测结果

        Raises:
            BacktestError: 回测失败
        """
        pass

    @abstractmethod
    def get_metrics(self, result: BacktestResult) -> StrategyMetrics:
        """
        获取策略指标。

        Args:
            result: 回测结果

        Returns:
            策略指标
        """
        pass

    def __enter__(self) -> "BacktestProvider":
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.disconnect()
