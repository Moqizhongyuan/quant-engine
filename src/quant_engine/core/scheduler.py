"""
交易调度器

负责交易时间管理和任务调度。
"""

from datetime import datetime, time
from typing import Callable, Optional

from quant_engine.utils.config import SchedulerConfig, get_settings
from quant_engine.utils.logger import get_logger

logger = get_logger(__name__)


class TradingScheduler:
    """
    交易调度器。

    管理交易时间段，判断当前是否为交易时间。
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """
        初始化调度器。

        Args:
            config: 调度配置
        """
        if config is None:
            config = get_settings().scheduler
        self._config = config

        self._morning_start = self._parse_time(config.trading_hours.morning_start)
        self._morning_end = self._parse_time(config.trading_hours.morning_end)
        self._afternoon_start = self._parse_time(config.trading_hours.afternoon_start)
        self._afternoon_end = self._parse_time(config.trading_hours.afternoon_end)
        self._signal_fetch_time = self._parse_time(config.signal_fetch_time)
        self._order_execute_time = self._parse_time(config.order_execute_time)

    def _parse_time(self, time_str: str) -> time:
        """
        解析时间字符串。

        Args:
            time_str: 时间字符串，格式 HH:MM

        Returns:
            time 对象
        """
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))

    def is_trading_time(self, dt: Optional[datetime] = None) -> bool:
        """
        判断是否为交易时间。

        Args:
            dt: 要判断的时间，默认为当前时间

        Returns:
            是否为交易时间
        """
        if dt is None:
            dt = datetime.now()

        if dt.weekday() >= 5:
            return False

        current_time = dt.time()

        in_morning = self._morning_start <= current_time <= self._morning_end
        in_afternoon = self._afternoon_start <= current_time <= self._afternoon_end

        return in_morning or in_afternoon

    def is_signal_fetch_time(self, dt: Optional[datetime] = None) -> bool:
        """
        判断是否为信号获取时间。

        Args:
            dt: 要判断的时间

        Returns:
            是否为信号获取时间
        """
        if dt is None:
            dt = datetime.now()

        current_time = dt.time()
        return (
            current_time.hour == self._signal_fetch_time.hour
            and current_time.minute == self._signal_fetch_time.minute
        )

    def is_order_execute_time(self, dt: Optional[datetime] = None) -> bool:
        """
        判断是否为订单执行时间。

        Args:
            dt: 要判断的时间

        Returns:
            是否为订单执行时间
        """
        if dt is None:
            dt = datetime.now()

        current_time = dt.time()
        return (
            current_time.hour == self._order_execute_time.hour
            and current_time.minute == self._order_execute_time.minute
        )

    def get_next_trading_time(self, dt: Optional[datetime] = None) -> Optional[datetime]:
        """
        获取下一个交易时间。

        Args:
            dt: 起始时间

        Returns:
            下一个交易时间或 None
        """
        if dt is None:
            dt = datetime.now()

        current_time = dt.time()

        if current_time < self._morning_start:
            return dt.replace(
                hour=self._morning_start.hour,
                minute=self._morning_start.minute,
                second=0,
                microsecond=0,
            )

        if self._morning_end < current_time < self._afternoon_start:
            return dt.replace(
                hour=self._afternoon_start.hour,
                minute=self._afternoon_start.minute,
                second=0,
                microsecond=0,
            )

        return None

    def get_trading_status(self) -> dict:
        """
        获取当前交易状态。

        Returns:
            交易状态信息
        """
        now = datetime.now()
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "is_trading_time": self.is_trading_time(now),
            "is_trading_day": now.weekday() < 5,
            "morning_session": f"{self._morning_start.strftime('%H:%M')} - {self._morning_end.strftime('%H:%M')}",
            "afternoon_session": f"{self._afternoon_start.strftime('%H:%M')} - {self._afternoon_end.strftime('%H:%M')}",
            "signal_fetch_time": self._signal_fetch_time.strftime("%H:%M"),
            "order_execute_time": self._order_execute_time.strftime("%H:%M"),
        }
