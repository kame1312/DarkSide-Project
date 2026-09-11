import aiosqlite


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        This function will add a warn to the database.

        :param user_id: The ID of the user that should be warned.
        :param reason: The reason why the user should be warned.
        """
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await self.connection.commit()
            return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        """
        This function will remove a warn from the database.

        :param warn_id: The ID of the warn.
        :param user_id: The ID of the user that was warned.
        :param server_id: The ID of the server where the user has been warned
        """
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        """
        This function will get all the warnings of a user.

        :param user_id: The ID of the user that should be checked.
        :param server_id: The ID of the server that should be checked.
        :return: A list of all the warnings of the user.
        """
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

    async def set_secnews_channel(self, server_id: int, channel_id: int) -> None:
        """
        This function will set (or replace) the channel used for security news in a server.

        :param server_id: The ID of the server to configure.
        :param channel_id: The ID of the channel where news should be sent.
        """
        await self.connection.execute(
            "INSERT INTO secnews_channels(server_id, channel_id) VALUES (?, ?) "
            "ON CONFLICT(server_id) DO UPDATE SET channel_id=excluded.channel_id",
            (
                server_id,
                channel_id,
            ),
        )
        await self.connection.commit()

    async def get_secnews_channels(self) -> dict:
        """
        This function will get all the configured security news channels.

        :return: A dict mapping server_id -> channel_id.
        """
        rows = await self.connection.execute(
            "SELECT server_id, channel_id FROM secnews_channels"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return {int(row[0]): int(row[1]) for row in result}

    async def set_secnews_last_seen(self, feed_url: str, entry_id: str) -> None:
        """
        This function will remember the last article seen for a given RSS feed.

        :param feed_url: The URL of the feed.
        :param entry_id: The ID (or link) of the latest article posted for that feed.
        """
        await self.connection.execute(
            "INSERT INTO secnews_last_seen(feed_url, entry_id) VALUES (?, ?) "
            "ON CONFLICT(feed_url) DO UPDATE SET entry_id=excluded.entry_id",
            (
                feed_url,
                entry_id,
            ),
        )
        await self.connection.commit()

    async def get_secnews_last_seen(self) -> dict:
        """
        This function will get the last-seen article ID for every RSS feed tracked so far.

        :return: A dict mapping feed_url -> entry_id.
        """
        rows = await self.connection.execute(
            "SELECT feed_url, entry_id FROM secnews_last_seen"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return {row[0]: row[1] for row in result}