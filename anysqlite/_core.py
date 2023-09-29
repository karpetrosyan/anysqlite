import sqlite3
import typing as tp
from functools import partial, wraps

from anyio import CapacityLimiter, to_thread

P = tp.ParamSpec("P")
T = tp.TypeVar("T")


def copy_signature(fnc: tp.Callable[P, T]):
    @wraps(fnc)
    def dec(fnc) -> tp.Callable[P, T]:
        def inner(*args, **kwargs) -> T:
            return fnc(*args, **kwargs)

        return inner

    return dec


def return_connection(
    fnc: tp.Callable[P, T]
) -> tp.Callable[P, tp.Coroutine[None, None, "Connection"]]:
    @wraps(fnc)
    def inner(*args, **kwargs):
        return fnc(*args, **kwargs)

    return inner


class Connection:
    def __init__(self, _real_connection: sqlite3.Connection) -> None:
        self._real_connection = _real_connection
        self._limiter = CapacityLimiter(1)

    @copy_signature(sqlite3.Connection.close)
    async def close(self, *args, **kwargs):
        return await to_thread.run_sync(
            self._real_connection.close, *args, **kwargs, limiter=self._limiter
        )

    @copy_signature(sqlite3.Connection.commit)
    async def commit(self, *args, **kwargs):
        return await to_thread.run_sync(
            self._real_connection.commit, *args, **kwargs, limiter=self._limiter
        )

    @copy_signature(sqlite3.Connection.rollback)
    async def rollback(self, *args, **kwargs):
        return await to_thread.run_sync(
            self._real_connection.rollback, *args, **kwargs, limiter=self._limiter
        )

    async def cursor(self, *args, **kwargs) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_connection.cursor, *args, **kwargs, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)


class Cursor:
    def __init__(self, real_cursor: sqlite3.Cursor, limiter: CapacityLimiter) -> None:
        self._real_cursor = real_cursor
        self._limiter = limiter

    @property
    def description(self) -> str:
        return self._real_cursor.description

    @property
    def rowcount(self) -> int:
        return self._real_cursor.rowcount

    @property
    def arraysize(self) -> int:
        return self._real_cursor.arraysize

    @copy_signature(sqlite3.Cursor.close)
    async def close(self, *args, **kwargs) -> None:
        await to_thread.run_sync(
            self._real_cursor.close, *args, **kwargs, limiter=self._limiter
        )

    @copy_signature(sqlite3.Cursor.execute)
    async def execute(self, *args, **kwargs) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_cursor.execute, *args, **kwargs, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    @copy_signature(sqlite3.Cursor.executemany)
    async def executemany(self, *args, **kwargs) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_cursor.executemany, *args, **kwargs, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    @copy_signature(sqlite3.Cursor.executescript)
    async def executescript(self, *args, **kwargs) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_cursor.executescript, *args, **kwargs, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    @copy_signature(sqlite3.Cursor.fetchone)
    async def fetchone(self, *args, **kwargs):
        return await to_thread.run_sync(
            self._real_cursor.fetchone, *args, **kwargs, limiter=self._limiter
        )

    @copy_signature(sqlite3.Cursor.fetchmany)
    async def fetchmany(self, *args, **kwargs):
        return await to_thread.run_sync(
            self._real_cursor.fetchmany, *args, **kwargs, limiter=self._limiter
        )

    @copy_signature(sqlite3.Cursor.fetchall)
    async def fetchall(self, *args, **kwargs):
        return await to_thread.run_sync(
            self._real_cursor.fetchall, *args, **kwargs, limiter=self._limiter
        )


@return_connection
@copy_signature(sqlite3.connect)
async def connect(*args, **kwargs) -> "Connection":
    if len(args) >= 5:
        args[4] = False

    if "check_same_thread" in kwargs:
        kwargs["check_same_thread"] = False

    real_connection = await to_thread.run_sync(
        partial(sqlite3.connect, *args, **kwargs, check_same_thread=False)
    )
    return Connection(real_connection)
