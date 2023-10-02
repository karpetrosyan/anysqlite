# anysqlite

Anysqlite provides an `async/await` interface to the standard `sqlite3` library and supports both `trio` and `asyncio` backends using the power of [Anyio](https://github.com/agronholm/anyio).


[![PyPI - Version](https://img.shields.io/pypi/v/anysqlite.svg)](https://pypi.org/project/anysqlite)
[![PyPI - Python Version](https://img.shields.io/pyp1i/pyversions/anysqlite.svg)](https://pypi.org/project/anysqlite)

-----

## Installation

```console
pip install anysqlite
```

## Basic usage

``` python
>>> import anysqlite
>>> 
>>> conn = await anysqlite.connect(":memory:")
>>> cursor = await conn.execute("SELECT DATETIME()")
>>> 
>>> response = await cursor.fetchone()
>>> print(response)
[('2023-10-02 13:42:42',)]
```