import pytest
import anysqlite

@pytest.mark.anyio
async def test_anysqlite():
    db = await anysqlite.connect(":memory:")
    
    try:
        cursor = await db.cursor()
        await cursor.execute("CREATE TABLE anysqlite_test(version TEXT)")
        await cursor.execute("INSERT INTO anysqlite_test VALUES(?)", [anysqlite.__version__])
        await cursor.execute("SELECT * FROM anysqlite_test")

        assert (anysqlite.__version__, ) == await cursor.fetchone()
    finally:
        await db.close()