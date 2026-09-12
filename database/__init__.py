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

    async def create_ticket(
        self, guild_id: int, channel_id: int, user_id: int, reason: str
    ) -> int:
        cursor = await self.connection.execute(
            "INSERT INTO tickets(guild_id, channel_id, user_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, channel_id, user_id, reason),
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def get_ticket(self, channel_id: int) -> dict | None:
        rows = await self.connection.execute(
            "SELECT id, guild_id, channel_id, user_id, reason, created_at, closed FROM tickets WHERE channel_id = ?",
            (channel_id,),
        )
        async with rows as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "guild_id": row[1],
                    "channel_id": row[2],
                    "user_id": row[3],
                    "reason": row[4],
                    "created_at": row[5],
                    "closed": row[6],
                }
        return None

    async def close_ticket(self, channel_id: int) -> None:
        await self.connection.execute(
            "UPDATE tickets SET closed = 1 WHERE channel_id = ?",
            (channel_id,),
        )
        await self.connection.commit()

    async def get_open_ticket_by_user(
        self, guild_id: int, user_id: int
    ) -> dict | None:
        rows = await self.connection.execute(
            "SELECT id, channel_id, user_id, reason, created_at FROM tickets WHERE guild_id = ? AND user_id = ? AND closed = 0",
            (guild_id, user_id),
        )
        async with rows as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "channel_id": row[1],
                    "user_id": row[2],
                    "reason": row[3],
                    "created_at": row[4],
                }
        return None

    async def get_ticket_config(self, guild_id: int) -> dict | None:
        rows = await self.connection.execute(
            "SELECT category_id, log_channel_id, support_role_id FROM ticket_config WHERE guild_id = ?",
            (guild_id,),
        )
        async with rows as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "category_id": int(row[0]) if row[0] else None,
                    "log_channel_id": int(row[1]) if row[1] else None,
                    "support_role_id": int(row[2]) if row[2] else None,
                }
        return None

    async def set_ticket_config(
        self,
        guild_id: int,
        category_id: int = None,
        log_channel_id: int = None,
        support_role_id: int = None,
    ) -> None:
        existing = await self.get_ticket_config(guild_id)
        if existing is None:
            await self.connection.execute(
                "INSERT INTO ticket_config(guild_id, category_id, log_channel_id, support_role_id) VALUES (?, ?, ?, ?)",
                (guild_id, category_id, log_channel_id, support_role_id),
            )
        else:
            new_category = category_id if category_id is not None else existing["category_id"]
            new_log = log_channel_id if log_channel_id is not None else existing["log_channel_id"]
            new_role = support_role_id if support_role_id is not None else existing["support_role_id"]
            await self.connection.execute(
                "UPDATE ticket_config SET category_id = ?, log_channel_id = ?, support_role_id = ? WHERE guild_id = ?",
                (new_category, new_log, new_role, guild_id),
            )
        await self.connection.commit()

    async def reset_ticket_config(self, guild_id: int) -> None:
        await self.connection.execute(
            "DELETE FROM ticket_config WHERE guild_id = ?",
            (guild_id,),
        )
        await self.connection.commit()