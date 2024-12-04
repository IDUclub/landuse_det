"""Connection manager class and get_connection function are defined here."""

from asyncio import Lock
from typing import AsyncIterator

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine


class PostgresConnectionManager:
    """Connection manager for PostgreSQL database"""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        pool_size: int = 10,
        application_name: str | None = None,
    ) -> None:
        """Initialize connection manager entity."""
        self._engine: AsyncEngine | None = None
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._pool_size = pool_size
        self._application_name = application_name
        self._lock = Lock()

    async def update(
        self,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        pool_size: int | None = None,
        application_name: str | None = None,
    ) -> None:
        """Initialize connection manager entity."""
        async with self._lock:  # pylint: disable=not-async-context-manager
            self._host = host or self._host
            self._port = port or self._port
            self._database = database or self._database
            self._user = user or self._user
            self._password = password or self._password
            self._pool_size = pool_size or self._pool_size
            self._application_name = application_name or self._application_name

            if self.initialized:
                await self.refresh()

    @property
    def initialized(self) -> bool:
        return self._engine is not None

    async def refresh(self) -> None:
        """(Re-)create connection engine."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

        logger.info(
            "Creating pool with max_size = {} on postgresql://{}@{}:{}/{}",
            self._pool_size,
            self._user,
            self._host,
            self._port,
            self._database,
        )
        self._engine = create_async_engine(
            f"postgresql+asyncpg://{self._user}:{self._password}@{self._host}:{self._port}/{self._database}",
            future=True,
            pool_size=max(1, self._pool_size - 5),
            max_overflow=5,
        )
        try:
            async with self._engine.connect() as conn:
                cur = await conn.execute(select(1))
                assert cur.fetchone()[0] == 1
        except Exception as exc:
            self._engine = None
            raise RuntimeError("something wrong with database connection, aborting") from exc

    async def shutdown(self) -> None:
        """Dispose connection pool and deinitialize."""
        if self._engine is not None:
            async with self._lock:  # pylint: disable=not-async-context-manager
                if self._engine is not None:
                    await self._engine.dispose()
                self._engine = None

    async def get_connection(self) -> AsyncIterator[AsyncConnection]:
        """Get an async connection to the database."""
        if self._engine is None:
            async with self._lock:  # pylint: disable=not-async-context-manager
                if self._engine is None:
                    await self.refresh()
        async with self._engine.connect() as conn:
            if self._application_name is not None:
                await conn.execute(text(f'SET application_name TO "{self._application_name}"'))
                await conn.commit()
            yield conn
