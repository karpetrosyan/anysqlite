import typing as tp
import sqlite3

P = tp.ParamSpec("P")
T = tp.TypeVar("T")
RT = tp.TypeVar("RT")

def copy_sig(_: tp.Callable[P, T], returns: tp.Callable[..., RT]) -> tp.Callable[[tp.Callable[..., tp.Any]], tp.Callable[P, RT]]:

    def decorator(fnc: tp.Callable[..., tp.Any]) -> tp.Callable[P, RT]:

        def inner(*args, **kwargs):
            return fnc(*args, **kwargs)
    
        return inner

    return decorator

@copy_sig(sqlite3.connect, int.__new__)
async def connect(*args, **kwargs):
    ...


tp.reveal_type(connect)
a = connect()
tp.reveal_type(a)