"""异常层次定义。"""


class QuantEngineError(Exception):
    """量化引擎基础异常。"""


class BrokerError(QuantEngineError):
    """券商适配器异常。"""


class BrokerConnectionError(BrokerError):
    """券商连接异常。"""


class OrderSubmitError(BrokerError):
    """下单异常。"""


class OrderCancelError(BrokerError):
    """撤单异常。"""


class ConfigError(QuantEngineError):
    """配置加载异常。"""
