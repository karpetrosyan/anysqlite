import sqlite3
import typing as tp
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from anyio import CapacityLimiter, to_thread

if TYPE_CHECKING:
    import sys
    from typing import Callable, TypeVar

    if sys.version_info >= (3, 11):
        from typing import TypeVarTuple, Unpack
    else:
        from typing_extensions import TypeVarTuple, Unpack

    T_Retval = TypeVar("T_Retval")
    PosArgsT = TypeVarTuple("PosArgsT")


class LimiterMixin:
    _limiter: CapacityLimiter

    async def _to_thread(
        self, func: "Callable[[Unpack[PosArgsT]], T_Retval]", *args: "Unpack[PosArgsT]"
    ) -> "T_Retval":
        return await to_thread.run_sync(func, *args, limiter=self._limiter)


class Connection(LimiterMixin):
    def __init__(self, _real_connection: sqlite3.Connection) -> None:
        self._real_connection = _real_connection
        self._limiter = CapacityLimiter(1)

    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        return await self.close()

    async def close(self) -> None:
        return await self._to_thread(self._real_connection.close)

    async def commit(self) -> None:
        return await self._to_thread(self._real_connection.commit)

    async def rollback(self) -> None:
        return await self._to_thread(self._real_connection.rollback)

    async def cursor(self) -> "Cursor":
        real_cursor = await self._to_thread(self._real_connection.cursor)
        return Cursor(real_cursor, self._limiter)

    async def execute(self, sql: str, parameters: tp.Iterable[tp.Any] = ()) -> "Cursor":
        real_cursor = await self._to_thread(
            self._real_connection.execute, sql, parameters  # type:ignore[arg-type]
        )
        return Cursor(real_cursor, self._limiter)

    async def executemany(
        self, sql: str, seq_of_parameters: tp.Iterable[tp.Iterable[tp.Any]]
    ) -> "Cursor":
        real_cursor = await self._to_thread(
            self._real_connection.executemany,  # type:ignore[arg-type]
            sql,
            seq_of_parameters,
        )
        return Cursor(real_cursor, self._limiter)

    async def executescript(self, sql_script: str) -> "Cursor":
        real_cursor = await self._to_thread(
            self._real_connection.executescript, sql_script
        )
        return Cursor(real_cursor, self._limiter)


class Cursor(LimiterMixin):
    def __init__(self, real_cursor: sqlite3.Cursor, limiter: CapacityLimiter) -> None:
        self._real_cursor = real_cursor
        self._limiter = limiter

    @property
    def description(
        self,
    ) -> tp.Union[
        tp.Tuple[tp.Tuple[str, None, None, None, None, None, None], ...], tp.Any
    ]:
        return self._real_cursor.description

    @property
    def rowcount(self) -> int:
        return self._real_cursor.rowcount

    @property
    def arraysize(self) -> int:
        return self._real_cursor.arraysize

    async def close(self) -> None:
        await self._to_thread(self._real_cursor.close)

    async def execute(self, sql: str, parameters: tp.Iterable[tp.Any] = ()) -> "Cursor":
        real_cursor = await self._to_thread(
            self._real_cursor.execute,  # type:ignore[arg-type]
            sql,
            parameters,
        )
        return Cursor(real_cursor, self._limiter)

    async def executemany(
        self, sql: str, seq_of_parameters: tp.Iterable[tp.Iterable[tp.Any]]
    ) -> "Cursor":
        real_cursor = await self._to_thread(
            self._real_cursor.executemany,  # type:ignore[arg-type]
            sql,
            seq_of_parameters,
        )
        return Cursor(real_cursor, self._limiter)

    async def executescript(self, sql_script: str) -> "Cursor":
        real_cursor = await self._to_thread(self._real_cursor.executescript, sql_script)
        return Cursor(real_cursor, self._limiter)

    async def fetchone(self) -> tp.Any:
        return await self._to_thread(self._real_cursor.fetchone)

    async def fetchmany(self, size: tp.Union[int, None] = 1) -> tp.Any:
        return await self._to_thread(self._real_cursor.fetchmany, size)

    async def fetchall(self) -> tp.Any:
        return await self._to_thread(self._real_cursor.fetchall)


async def connect(
    database: tp.Union[str, bytes, Path], **kwargs: tp.Any
) -> "Connection":
    kwargs["check_same_thread"] = False
    real_connection = await to_thread.run_sync(
        partial(sqlite3.connect, database, **kwargs)
    )
    return Connection(real_connection)
