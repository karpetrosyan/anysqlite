import asyncio
import sqlite3
import typing as tp
from functools import partial
from queue import Queue
from threading import Event, Thread

import sniffio

try:
    import trio
except ImportError:  # pragma: no cover
    trio = None  # type: ignore

__all__ = ["connect", "Connection", "Cursor"]

P = tp.ParamSpec("P")
T = tp.TypeVar("T")

apilevel = "2.0"
threadsafety = sqlite3.threadsafety
paramstyle = sqlite3.paramstyle


def copy_signature(fnc: tp.Callable[P, T]):
    def dec(fnc) -> tp.Callable[P, T]:
        def inner(*args, **kwargs) -> T:
            return fnc(*args, **kwargs)

        return inner

    return dec


class Future:
    def __init__(self, task: tp.Callable[..., tp.Any]) -> None:
        self.fnc = task

    def result(self):
        if hasattr(self, "_result"):
            return self._result

        if hasattr(self, "_exc"):
            raise self._exc

        raise RuntimeError("Invalid state")

    def set_result(self, value: tp.Any) -> None:
        self._result = value

    def set_exception(self, exc: BaseException) -> None:
        self._exc = exc

    def done(self) -> bool:
        return hasattr(self, "_result") or hasattr(self, "_exc")

    async def _await(self):
        backend = sniffio.current_async_library()
        while True:
            if self.done():
                return self.result()

            if backend == "trio":
                await trio.sleep(0.0000001)
            elif backend == "asyncio":
                await asyncio.sleep(0.0000001)

    def __await__(self):
        return self._await().__await__()


class Connection:
    def __init__(self, database: str) -> None:
        self._database = database
        self._real_connection: tp.Union[sqlite3.Connection, None] = None
        self._running = True
        self._queue: Queue[Future] = Queue()
        connected = Event()
        Thread(target=self.run, args=(connected,), daemon=True).start()
        connected.wait()

    def run(self, connected: Event):
        self._real_connection = sqlite3.connect(self._database)
        connected.set()

        while self._running:
            future = self._queue.get()

            try:
                result = future.fnc()
                future.set_result(result)
            except BaseException as exc:
                future.set_exception(exc)

    async def _execute(self, fnc: tp.Callable[..., tp.Any]):
        fut = Future(fnc)
        self._queue.put(fut)
        return await fut

    @copy_signature(sqlite3.Connection.close)
    async def close(self, *args, **kwargs):
        return await self._execute(
            partial(self._real_connection.close, *args, **kwargs)
        )

    @copy_signature(sqlite3.Connection.commit)
    async def commit(self, *args, **kwargs):
        return await self._execute(
            partial(self._real_connection.commit, *args, **kwargs)
        )

    @copy_signature(sqlite3.Connection.rollback)
    async def rollback(self, *args, **kwargs):
        return await self._execute(
            partial(self._real_connection.rollback, *args, **kwargs)
        )

    async def cursor(self, *args, **kwargs) -> "Cursor":
        return Cursor(
            conn=self,
            real_cursor=await self._execute(
                partial(self._real_connection.cursor, *args, **kwargs)
            ),
        )


class Cursor:
    def __init__(self, conn: Connection, real_cursor: sqlite3.Cursor) -> None:
        self._connection = conn
        self._real_cursor = real_cursor

    @property
    @copy_signature(sqlite3.Cursor.description)
    def description(self):
        return self._real_cursor.description

    @property
    @copy_signature(sqlite3.Cursor.rowcount)
    def rowcount(self):
        return self._real_cursor.rowcount

    @copy_signature(sqlite3.Cursor.close)
    async def close(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.close, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.execute)
    async def execute(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.execute, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.executemany)
    async def executemany(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.executemany, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.fetchone)
    async def fetchone(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.fetchone, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.fetchmany)
    async def fetchmany(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.fetchmany, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.fetchall)
    async def fetchall(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.fetchall, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.arraysize)
    async def arraysize(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.arraysize, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.setinputsizes)
    async def setinputsizes(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.setinputsizes, *args, **kwargs)
        )

    @copy_signature(sqlite3.Cursor.setoutputsize)
    async def setoutputsize(self, *args, **kwargs):
        return await self._connection._execute(
            partial(self._real_cursor.setoutputsize, *args, **kwargs)
        )


def connect(database: str) -> Connection:
    return Connection(database)
