"""
自定义异常类型

定义系统中使用的异常类型。
"""


class QuantEngineError(Exception):
    """量化引擎基础异常"""

    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ConfigError(QuantEngineError):
    """配置错误"""

    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR")


class ConnectionError(QuantEngineError):
    """连接错误"""

    def __init__(self, message: str):
        super().__init__(message, "CONNECTION_ERROR")


class AuthenticationError(QuantEngineError):
    """认证错误"""

    def __init__(self, message: str):
        super().__init__(message, "AUTH_ERROR")


class DataFetchError(QuantEngineError):
    """数据获取错误"""

    def __init__(self, message: str):
        super().__init__(message, "DATA_FETCH_ERROR")


class OrderError(QuantEngineError):
    """订单错误"""

    def __init__(self, message: str):
        super().__init__(message, "ORDER_ERROR")


class OrderSubmitError(OrderError):
    """订单提交错误"""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "ORDER_SUBMIT_ERROR"


class OrderCancelError(OrderError):
    """订单撤销错误"""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "ORDER_CANCEL_ERROR"


class RiskControlError(QuantEngineError):
    """风控错误"""

    def __init__(self, message: str, rule: str = ""):
        super().__init__(message, "RISK_CONTROL_ERROR")
        self.rule = rule


class PositionLimitError(RiskControlError):
    """持仓限制错误"""

    def __init__(self, message: str):
        super().__init__(message, "POSITION_LIMIT")


class StopLossError(RiskControlError):
    """止损触发错误"""

    def __init__(self, message: str):
        super().__init__(message, "STOP_LOSS")


class DailyLossLimitError(RiskControlError):
    """单日亏损限制错误"""

    def __init__(self, message: str):
        super().__init__(message, "DAILY_LOSS_LIMIT")


class BrokerError(QuantEngineError):
    """券商接口错误"""

    def __init__(self, message: str):
        super().__init__(message, "BROKER_ERROR")


class BrokerNotConnectedError(BrokerError):
    """券商未连接错误"""

    def __init__(self, message: str = "券商接口未连接"):
        super().__init__(message)
        self.code = "BROKER_NOT_CONNECTED"


class BacktestError(QuantEngineError):
    """回测错误"""

    def __init__(self, message: str):
        super().__init__(message, "BACKTEST_ERROR")


class ValidationError(QuantEngineError):
    """数据验证错误"""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class TimeoutError(QuantEngineError):
    """超时错误"""

    def __init__(self, message: str, timeout: int = 0):
        super().__init__(message, "TIMEOUT_ERROR")
        self.timeout = timeout
