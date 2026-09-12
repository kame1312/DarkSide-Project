# DarkSide Protect

A multifunctional Discord bot built with `discord.py` that provides robust moderation tools, comprehensive server information, owner utilities, and an automated cybersecurity news feed system.

## Features

### 🛡️ Moderation
- **Kick / Ban / Hackban**: Manage members with detailed reasons and DM notifications.
- **Nickname Management**: Change or reset member nicknames.
- **Warning System**: Add, remove, and list warnings for users (backed by SQLite).
- **Purge**: Bulk delete messages from a channel.
- **Archive**: Save the last messages of a channel into a text file.
- **Mute / Unmute**: Temporarily timeout users using Discord's native timeout feature.

### 📰 Security News
- Automated RSS feed fetching from over 30 cybersecurity sources (The Hacker News, BleepingComputer, Krebs on Security, etc.).
- Configurable channel via `secnews setchannel`.
- Manual trigger via `secnews test` for immediate checks.

### ⚙️ General
- **Help**: Dynamically generated help menu listing all available commands.
- **Server Info**: Detailed statistics about the current server.
- **Ping**: Check the bot's latency.
- **Invite**: Get the bot's OAuth2 invite link.

### 👑 Owner
- **Cog Management**: Load, unload, and reload extensions on the fly.
- **Sync / Unsync**: Manage Discord slash commands synchronization.
- **Say / Embed**: Make the bot send custom messages.
- **Shutdown**: Safely shut down the bot.
- **Bot Info**: Display real-time CPU usage, RAM consumption, uptime, and system information.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE.md](LICENSE.md) file for details
