from functools import wraps
from typing import Callable
from typing import TypeVar
from typing import Awaitable
from typing import ParamSpec


P = ParamSpec("P")
T = TypeVar("T")


def to_async(fn: Callable[P, T], to_thread: bool = False) -> Callable[P, Awaitable[T]]:
    """
    Converts a synchronous function into an async function with option to run in a seperate thread
    """

    if to_thread:
        import asyncio

        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    else:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return fn(*args, **kwargs)  # Direct call, no threading

    return wrapper

