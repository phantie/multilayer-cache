import pytest 


@pytest.mark.asyncio
async def test_to_async():
    from multilayer_cache.util import to_async

    def add(a: int, b: int) -> int:
        return a + b

    add(1, 2) == 3
    await to_async(add, to_thread=False)(1, 2) == 3
    await to_async(add, to_thread=True)(1, 2) == 3

