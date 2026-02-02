"""
数据库连接管理模块

提供数据库连接、会话管理功能。
"""

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Generator, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from quant_engine.models.order import OrderDirection, OrderStatus, OrderType
from quant_engine.models.signal import SignalDirection
from quant_engine.utils.config import get_settings
from quant_engine.utils.logger import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class OrderTable(Base):
    """订单表"""

    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(OrderDirection), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 4))
    order_type = Column(Enum(OrderType), default=OrderType.LIMIT)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)

    filled_quantity = Column(Integer, default=0)
    filled_price = Column(Numeric(12, 4))
    broker_order_id = Column(String(50), index=True)

    signal_id = Column(String(36), index=True)
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PositionTable(Base):
    """持仓表"""

    __tablename__ = "positions"

    id = Column(String(36), primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(50))

    quantity = Column(Integer, default=0)
    available_quantity = Column(Integer, default=0)
    frozen_quantity = Column(Integer, default=0)

    avg_cost = Column(Numeric(12, 4), default=0)
    current_price = Column(Numeric(12, 4), default=0)

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SignalTable(Base):
    """交易信号表"""

    __tablename__ = "signals"

    id = Column(String(36), primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(50))

    direction = Column(Enum(SignalDirection), nullable=False)
    target_quantity = Column(Integer, nullable=False)
    target_price = Column(Numeric(12, 4))
    target_ratio = Column(Numeric(8, 4))

    source = Column(String(50), default="manual", index=True)
    strategy_name = Column(String(100))
    reason = Column(Text)

    executed = Column(Boolean, default=False, index=True)
    order_id = Column(String(36), index=True)

    created_at = Column(DateTime, default=datetime.now, index=True)
    executed_at = Column(DateTime)


class TradeLogTable(Base):
    """交易日志表"""

    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(10), nullable=False, index=True)
    message = Column(Text, nullable=False)
    context = Column(JSON)
    created_at = Column(DateTime, default=datetime.now, index=True)


class AccountSnapshotTable(Base):
    """账户快照表"""

    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(50), nullable=False, index=True)

    total_asset = Column(Numeric(16, 2), nullable=False)
    cash = Column(Numeric(16, 2), nullable=False)
    market_value = Column(Numeric(16, 2), nullable=False)
    total_profit_loss = Column(Numeric(16, 2), nullable=False)

    snapshot_date = Column(DateTime, default=datetime.now, index=True)


class Database:
    """数据库管理类"""

    def __init__(self, url: Optional[str] = None, echo: bool = False):
        """
        初始化数据库连接。

        Args:
            url: 数据库连接URL
            echo: 是否打印SQL语句
        """
        if url is None:
            settings = get_settings()
            url = settings.database.url
            echo = settings.database.echo

        self._engine = create_engine(url, echo=echo)
        self._session_factory = sessionmaker(bind=self._engine)
        logger.info(f"数据库连接已初始化: {url.split('@')[-1] if '@' in url else url}")

    def create_tables(self) -> None:
        """创建所有表"""
        Base.metadata.create_all(self._engine)
        logger.info("数据库表已创建")

    def drop_tables(self) -> None:
        """删除所有表"""
        Base.metadata.drop_all(self._engine)
        logger.warning("数据库表已删除")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话（上下文管理器）。

        Yields:
            Session 实例
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """
        获取数据库会话（需手动管理）。

        Returns:
            Session 实例
        """
        return self._session_factory()


_database: Optional[Database] = None


def get_database() -> Database:
    """
    获取全局数据库实例（单例模式）。

    Returns:
        Database 实例
    """
    global _database
    if _database is None:
        _database = Database()
    return _database


def init_database(url: Optional[str] = None) -> Database:
    """
    初始化数据库。

    Args:
        url: 数据库连接URL

    Returns:
        Database 实例
    """
    global _database
    _database = Database(url)
    _database.create_tables()
    return _database
