"""
量化交易平台 CLI 主入口

提供命令行交互界面。
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from quant_engine.cli import signal_cmd, order_cmd, position_cmd, account_cmd, risk_cmd, config_cmd, db_cmd

app = typer.Typer(
    name="quant-engine",
    help="量化交易平台 - A股日频交易系统",
    add_completion=False,
)

console = Console()

app.add_typer(signal_cmd.app, name="signal", help="信号管理")
app.add_typer(order_cmd.app, name="order", help="订单管理")
app.add_typer(position_cmd.app, name="position", help="持仓管理")
app.add_typer(account_cmd.app, name="account", help="账户管理")
app.add_typer(risk_cmd.app, name="risk", help="风控管理")
app.add_typer(config_cmd.app, name="config", help="配置管理")
app.add_typer(db_cmd.app, name="db", help="数据库管理")


@app.command()
def version():
    """显示版本信息"""
    from quant_engine import __version__
    console.print(f"quant-engine version {__version__}")


@app.command()
def status():
    """显示系统状态"""
    from quant_engine.core.scheduler import TradingScheduler
    from quant_engine.utils.config import get_settings

    settings = get_settings()
    scheduler = TradingScheduler()
    trading_status = scheduler.get_trading_status()

    table = Table(title="系统状态")
    table.add_column("项目", style="cyan")
    table.add_column("状态", style="green")

    table.add_row("当前时间", trading_status["current_time"])
    table.add_row("交易日", "是" if trading_status["is_trading_day"] else "否")
    table.add_row("交易时段", "是" if trading_status["is_trading_time"] else "否")
    table.add_row("上午时段", trading_status["morning_session"])
    table.add_row("下午时段", trading_status["afternoon_session"])
    table.add_row("信号获取时间", trading_status["signal_fetch_time"])
    table.add_row("订单执行时间", trading_status["order_execute_time"])
    table.add_row("风控状态", "启用" if settings.risk.enabled else "禁用")
    table.add_row("模拟交易", "是" if settings.broker.miniqmt.simulation else "否")

    console.print(table)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细日志"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件路径"),
):
    """
    量化交易平台 CLI

    使用 --help 查看各子命令的帮助信息。
    """
    if verbose:
        from quant_engine.utils.logger import setup_logger
        setup_logger(level="DEBUG")

    if config:
        from quant_engine.utils.config import reload_settings
        reload_settings(config)


if __name__ == "__main__":
    app()
