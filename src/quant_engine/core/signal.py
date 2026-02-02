"""
信号处理器

负责信号的获取、处理和转换。
"""

from datetime import datetime
from typing import List, Optional

from quant_engine.adapters.data import DataProvider
from quant_engine.models.signal import TradingSignal
from quant_engine.storage.repository import SignalRepository
from quant_engine.utils.logger import get_logger

logger = get_logger(__name__)


class SignalProcessor:
    """
    信号处理器。

    负责从数据源获取信号、存储和管理。
    """

    def __init__(
        self,
        data_provider: DataProvider,
        signal_repo: Optional[SignalRepository] = None,
    ):
        """
        初始化信号处理器。

        Args:
            data_provider: 数据源适配器
            signal_repo: 信号仓库
        """
        self._data_provider = data_provider
        self._signal_repo = signal_repo or SignalRepository()

    def fetch_signals(self) -> List[TradingSignal]:
        """
        从数据源获取信号。

        Returns:
            交易信号列表
        """
        logger.info(f"从 {self._data_provider.name} 获取信号...")

        if not self._data_provider.is_connected:
            self._data_provider.connect()

        signals = self._data_provider.fetch_signals()

        if signals:
            self._signal_repo.save_batch(signals)
            logger.info(f"获取到 {len(signals)} 个信号并已保存")
        else:
            logger.info("未获取到新信号")

        return signals

    def get_pending_signals(self) -> List[TradingSignal]:
        """
        获取待执行信号。

        Returns:
            待执行信号列表
        """
        return self._signal_repo.get_pending_signals()

    def list_signals(
        self,
        source: Optional[str] = None,
        executed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TradingSignal]:
        """
        查询信号列表。

        Args:
            source: 信号来源筛选
            executed: 是否已执行筛选
            start_date: 开始日期
            limit: 返回数量限制

        Returns:
            信号列表
        """
        return self._signal_repo.list_signals(source, executed, start_date, limit)

    def mark_signal_executed(self, signal: TradingSignal) -> None:
        """
        标记信号已执行。

        Args:
            signal: 信号
        """
        self._signal_repo.save(signal)
