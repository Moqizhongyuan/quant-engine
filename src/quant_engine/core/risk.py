"""
风控模块

提供交易风险控制功能。
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from quant_engine.models.account import Account
from quant_engine.models.order import Order, OrderDirection
from quant_engine.models.position import Position
from quant_engine.utils.config import RiskConfig, get_settings
from quant_engine.utils.exceptions import (
    DailyLossLimitError,
    PositionLimitError,
    RiskControlError,
    StopLossError,
)
from quant_engine.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskCheckResult:
    """风控检查结果"""

    passed: bool
    rule: str
    message: str
    details: Optional[dict] = None


class RiskManager:
    """
    风控管理器。

    提供止损、仓位限制、单日亏损限制等风控检查。
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        """
        初始化风控管理器。

        Args:
            config: 风控配置，None 则使用默认配置
        """
        if config is None:
            config = get_settings().risk
        self._config = config
        self._daily_loss = Decimal("0")
        self._initial_asset = Decimal("0")

    @property
    def enabled(self) -> bool:
        """是否启用风控"""
        return self._config.enabled

    def set_initial_asset(self, asset: Decimal) -> None:
        """
        设置初始资产（用于计算日内亏损）。

        Args:
            asset: 初始资产
        """
        self._initial_asset = asset
        self._daily_loss = Decimal("0")

    def reset_daily_loss(self) -> None:
        """重置日内亏损统计"""
        self._daily_loss = Decimal("0")

    def check_order(
        self,
        order: Order,
        account: Account,
        positions: List[Position],
    ) -> RiskCheckResult:
        """
        检查订单是否通过风控。

        Args:
            order: 待检查的订单
            account: 账户信息
            positions: 当前持仓列表

        Returns:
            风控检查结果
        """
        if not self._config.enabled:
            return RiskCheckResult(passed=True, rule="disabled", message="风控已禁用")

        checks = [
            self._check_order_amount(order),
            self._check_position_limit(order, account, positions),
            self._check_holdings_limit(order, positions),
            self._check_daily_loss(account),
        ]

        for result in checks:
            if not result.passed:
                logger.warning(f"风控检查未通过: {result.rule} - {result.message}")
                return result

        return RiskCheckResult(passed=True, rule="all", message="所有风控检查通过")

    def check_all(
        self,
        account: Account,
        positions: List[Position],
    ) -> List[RiskCheckResult]:
        """
        执行所有风控检查。

        Args:
            account: 账户信息
            positions: 当前持仓列表

        Returns:
            所有检查结果列表
        """
        results = []

        results.append(self._check_daily_loss(account))

        for position in positions:
            results.append(self._check_stop_loss(position))
            results.append(self._check_take_profit(position))
            results.append(self._check_single_position_ratio(position, account))

        return results

    def _check_order_amount(self, order: Order) -> RiskCheckResult:
        """
        检查单笔交易金额。

        Args:
            order: 订单

        Returns:
            检查结果
        """
        if order.price is None:
            return RiskCheckResult(
                passed=True,
                rule="order_amount",
                message="市价单跳过金额检查",
            )

        amount = order.price * order.quantity
        max_amount = Decimal(str(self._config.max_order_amount))

        if amount > max_amount:
            return RiskCheckResult(
                passed=False,
                rule="order_amount",
                message=f"单笔交易金额 {amount:.2f} 超过限制 {max_amount:.2f}",
                details={"amount": float(amount), "limit": float(max_amount)},
            )

        return RiskCheckResult(
            passed=True,
            rule="order_amount",
            message="单笔交易金额检查通过",
        )

    def _check_position_limit(
        self,
        order: Order,
        account: Account,
        positions: List[Position],
    ) -> RiskCheckResult:
        """
        检查单只股票持仓比例限制。

        Args:
            order: 订单
            account: 账户
            positions: 持仓列表

        Returns:
            检查结果
        """
        if order.direction == OrderDirection.SELL:
            return RiskCheckResult(
                passed=True,
                rule="position_limit",
                message="卖出订单跳过持仓比例检查",
            )

        current_position = next(
            (p for p in positions if p.symbol == order.symbol),
            None,
        )
        current_value = current_position.market_value if current_position else Decimal("0")

        order_value = (order.price or Decimal("0")) * order.quantity
        total_value = current_value + order_value

        max_ratio = Decimal(str(self._config.max_position_ratio))
        max_value = account.total_asset * max_ratio

        if total_value > max_value:
            return RiskCheckResult(
                passed=False,
                rule="position_limit",
                message=f"股票 {order.symbol} 持仓将达到 {total_value:.2f}，超过限制 {max_value:.2f} ({max_ratio*100:.0f}%)",
                details={
                    "symbol": order.symbol,
                    "current_value": float(current_value),
                    "order_value": float(order_value),
                    "total_value": float(total_value),
                    "limit": float(max_value),
                },
            )

        return RiskCheckResult(
            passed=True,
            rule="position_limit",
            message="持仓比例检查通过",
        )

    def _check_holdings_limit(
        self,
        order: Order,
        positions: List[Position],
    ) -> RiskCheckResult:
        """
        检查持仓股票数量限制。

        Args:
            order: 订单
            positions: 持仓列表

        Returns:
            检查结果
        """
        if order.direction == OrderDirection.SELL:
            return RiskCheckResult(
                passed=True,
                rule="holdings_limit",
                message="卖出订单跳过持仓数量检查",
            )

        current_symbols = {p.symbol for p in positions if p.quantity > 0}
        is_new_position = order.symbol not in current_symbols

        if is_new_position and len(current_symbols) >= self._config.max_holdings:
            return RiskCheckResult(
                passed=False,
                rule="holdings_limit",
                message=f"持仓股票数量已达上限 {self._config.max_holdings}",
                details={
                    "current_holdings": len(current_symbols),
                    "limit": self._config.max_holdings,
                },
            )

        return RiskCheckResult(
            passed=True,
            rule="holdings_limit",
            message="持仓数量检查通过",
        )

    def _check_daily_loss(self, account: Account) -> RiskCheckResult:
        """
        检查单日亏损限制。

        Args:
            account: 账户信息

        Returns:
            检查结果
        """
        if self._initial_asset <= 0:
            return RiskCheckResult(
                passed=True,
                rule="daily_loss",
                message="未设置初始资产，跳过日内亏损检查",
            )

        daily_loss = self._initial_asset - account.total_asset
        loss_ratio = daily_loss / self._initial_asset
        max_loss_ratio = Decimal(str(self._config.max_daily_loss_ratio))

        if loss_ratio > max_loss_ratio:
            return RiskCheckResult(
                passed=False,
                rule="daily_loss",
                message=f"日内亏损 {loss_ratio*100:.2f}% 超过限制 {max_loss_ratio*100:.0f}%",
                details={
                    "daily_loss": float(daily_loss),
                    "loss_ratio": float(loss_ratio),
                    "limit": float(max_loss_ratio),
                },
            )

        return RiskCheckResult(
            passed=True,
            rule="daily_loss",
            message=f"日内亏损 {loss_ratio*100:.2f}% 在限制范围内",
        )

    def _check_stop_loss(self, position: Position) -> RiskCheckResult:
        """
        检查止损。

        Args:
            position: 持仓

        Returns:
            检查结果
        """
        if position.quantity <= 0:
            return RiskCheckResult(
                passed=True,
                rule="stop_loss",
                message="无持仓，跳过止损检查",
            )

        loss_ratio = -position.profit_loss_ratio
        stop_loss_ratio = Decimal(str(self._config.stop_loss_ratio))

        if loss_ratio >= stop_loss_ratio:
            return RiskCheckResult(
                passed=False,
                rule="stop_loss",
                message=f"股票 {position.symbol} 亏损 {loss_ratio*100:.2f}% 触发止损线 {stop_loss_ratio*100:.0f}%",
                details={
                    "symbol": position.symbol,
                    "loss_ratio": float(loss_ratio),
                    "stop_loss_ratio": float(stop_loss_ratio),
                    "quantity": position.quantity,
                },
            )

        return RiskCheckResult(
            passed=True,
            rule="stop_loss",
            message=f"股票 {position.symbol} 未触发止损",
        )

    def _check_take_profit(self, position: Position) -> RiskCheckResult:
        """
        检查止盈。

        Args:
            position: 持仓

        Returns:
            检查结果
        """
        if position.quantity <= 0:
            return RiskCheckResult(
                passed=True,
                rule="take_profit",
                message="无持仓，跳过止盈检查",
            )

        profit_ratio = position.profit_loss_ratio
        take_profit_ratio = Decimal(str(self._config.take_profit_ratio))

        if profit_ratio >= take_profit_ratio:
            return RiskCheckResult(
                passed=False,
                rule="take_profit",
                message=f"股票 {position.symbol} 盈利 {profit_ratio*100:.2f}% 触发止盈线 {take_profit_ratio*100:.0f}%",
                details={
                    "symbol": position.symbol,
                    "profit_ratio": float(profit_ratio),
                    "take_profit_ratio": float(take_profit_ratio),
                    "quantity": position.quantity,
                },
            )

        return RiskCheckResult(
            passed=True,
            rule="take_profit",
            message=f"股票 {position.symbol} 未触发止盈",
        )

    def _check_single_position_ratio(
        self,
        position: Position,
        account: Account,
    ) -> RiskCheckResult:
        """
        检查单只股票持仓比例。

        Args:
            position: 持仓
            account: 账户

        Returns:
            检查结果
        """
        if account.total_asset <= 0:
            return RiskCheckResult(
                passed=True,
                rule="single_position_ratio",
                message="总资产为0，跳过检查",
            )

        ratio = position.market_value / account.total_asset
        max_ratio = Decimal(str(self._config.max_position_ratio))

        if ratio > max_ratio:
            return RiskCheckResult(
                passed=False,
                rule="single_position_ratio",
                message=f"股票 {position.symbol} 持仓比例 {ratio*100:.2f}% 超过限制 {max_ratio*100:.0f}%",
                details={
                    "symbol": position.symbol,
                    "ratio": float(ratio),
                    "limit": float(max_ratio),
                },
            )

        return RiskCheckResult(
            passed=True,
            rule="single_position_ratio",
            message=f"股票 {position.symbol} 持仓比例正常",
        )

    def validate_order_or_raise(
        self,
        order: Order,
        account: Account,
        positions: List[Position],
    ) -> None:
        """
        验证订单，不通过则抛出异常。

        Args:
            order: 订单
            account: 账户
            positions: 持仓列表

        Raises:
            RiskControlError: 风控检查不通过
        """
        result = self.check_order(order, account, positions)
        if not result.passed:
            if result.rule == "position_limit":
                raise PositionLimitError(result.message)
            elif result.rule == "daily_loss":
                raise DailyLossLimitError(result.message)
            elif result.rule == "stop_loss":
                raise StopLossError(result.message)
            else:
                raise RiskControlError(result.message, result.rule)
