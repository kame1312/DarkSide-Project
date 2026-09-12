import aiosqlite


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (warn_id, user_id, server_id, moderator_id, reason),
            )
            await self.connection.commit()
            return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (warn_id, user_id, server_id),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

    async def set_secnews_channel(self, server_id: int, channel_id: int) -> None:
        await self.connection.execute(
            "INSERT INTO secnews_channels(server_id, channel_id) VALUES (?, ?) "
            "ON CONFLICT(server_id) DO UPDATE SET channel_id=excluded.channel_id",
            (server_id, channel_id),
        )
        await self.connection.commit()

    async def get_secnews_channels(self) -> dict:
        rows = await self.connection.execute(
            "SELECT server_id, channel_id FROM secnews_channels"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return {int(row[0]): int(row[1]) for row in result}

    async def set_secnews_last_seen(self, feed_url: str, entry_id: str) -> None:
        await self.connection.execute(
            "INSERT INTO secnews_last_seen(feed_url, entry_id) VALUES (?, ?) "
            "ON CONFLICT(feed_url) DO UPDATE SET entry_id=excluded.entry_id",
            (feed_url, entry_id),
        )
        await self.connection.commit()

    async def get_secnews_last_seen(self) -> dict:
        rows = await self.connection.execute(
            "SELECT feed_url, entry_id FROM secnews_last_seen"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return {row[0]: row[1] for row in result}

    async def set_ai_channel(self, server_id: int, channel_id: int) -> None:
        await self.connection.execute(
            "INSERT INTO ai_channels(server_id, channel_id) VALUES (?, ?) "
            "ON CONFLICT(server_id) DO UPDATE SET channel_id=excluded.channel_id",
            (server_id, channel_id),
        )
        await self.connection.commit()

    async def get_ai_channel(self, server_id: int) -> int | None:
        rows = await self.connection.execute(
            "SELECT channel_id FROM ai_channels WHERE server_id = ?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return int(result[0]) if result else None