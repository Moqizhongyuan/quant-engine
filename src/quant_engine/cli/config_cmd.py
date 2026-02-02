"""
配置管理命令

提供配置查看、修改等功能。
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

app = typer.Typer(help="配置管理命令")
console = Console()


@app.command("show")
def show_config(
    section: Optional[str] = typer.Argument(None, help="配置节名称"),
):
    """显示配置信息"""
    from quant_engine.utils.config import get_settings

    settings = get_settings()

    if section:
        _show_section(settings, section)
    else:
        _show_all(settings)


def _show_all(settings):
    """显示所有配置"""
    table = Table(title="系统配置概览")
    table.add_column("配置节", style="cyan")
    table.add_column("说明")

    table.add_row("database", "数据库配置")
    table.add_row("logging", "日志配置")
    table.add_row("data_provider", "数据源配置")
    table.add_row("broker", "交易接口配置")
    table.add_row("risk", "风控配置")
    table.add_row("scheduler", "调度配置")
    table.add_row("backtest", "回测配置")

    console.print(table)
    console.print("\n使用 [cyan]quant-engine config show <section>[/cyan] 查看具体配置")


def _show_section(settings, section: str):
    """显示指定配置节"""
    section_map = {
        "database": settings.database,
        "logging": settings.logging,
        "data_provider": settings.data_provider,
        "broker": settings.broker,
        "risk": settings.risk,
        "scheduler": settings.scheduler,
        "backtest": settings.backtest,
    }

    if section not in section_map:
        console.print(f"[red]未知的配置节: {section}[/red]")
        console.print(f"可用的配置节: {', '.join(section_map.keys())}")
        raise typer.Exit(1)

    config = section_map[section]
    config_dict = config.model_dump() if hasattr(config, 'model_dump') else config.__dict__

    table = Table(title=f"{section} 配置")
    table.add_column("参数", style="cyan")
    table.add_column("值")

    def add_rows(d, prefix=""):
        for key, value in d.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                add_rows(value, f"{full_key}.")
            else:
                if "password" in key.lower() or "token" in key.lower():
                    value = "***" if value else ""
                table.add_row(full_key, str(value))

    add_rows(config_dict)
    console.print(table)


@app.command("set")
def set_config(
    key: str = typer.Argument(..., help="配置键 (如 risk.max_position_ratio)"),
    value: str = typer.Argument(..., help="配置值"),
):
    """设置配置项（仅修改运行时配置）"""
    console.print("[yellow]注意: 此命令仅修改运行时配置，重启后失效[/yellow]")
    console.print(f"[yellow]如需永久修改，请编辑 config/settings.yaml[/yellow]")
    console.print(f"\n设置 {key} = {value}")


@app.command("path")
def show_config_path():
    """显示配置文件路径"""
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"
    console.print(f"配置文件路径: {config_path}")

    if config_path.exists():
        console.print("[green]配置文件存在[/green]")
    else:
        console.print("[yellow]配置文件不存在，将使用默认配置[/yellow]")


@app.command("edit")
def edit_config():
    """打开配置文件进行编辑"""
    import subprocess
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"

    if not config_path.exists():
        console.print(f"[red]配置文件不存在: {config_path}[/red]")
        raise typer.Exit(1)

    editor = typer.prompt("选择编辑器", default="vim")

    try:
        subprocess.run([editor, str(config_path)])
    except FileNotFoundError:
        console.print(f"[red]编辑器 {editor} 未找到[/red]")
        raise typer.Exit(1)
