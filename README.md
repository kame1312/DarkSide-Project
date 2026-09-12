# DarkSide Protect

A multifunctional Discord bot built with `discord.py` that provides robust moderation tools, comprehensive server information, owner utilities, an automated cybersecurity news feed system, an integrated AI assistant powered by Groq, and a fully configurable ticket system.

## Features

### 🛡️ Moderation
- **Kick / Ban / Hackban**: Manage members with detailed reasons and DM notifications.
- **Nickname Management**: Change or reset member nicknames.
- **Warning System**: Add, remove, and list warnings for users (backed by SQLite).
- **Purge**: Bulk delete messages from a channel.
- **Archive**: Save the last messages of a channel into a text file.
- **Mute / Unmute**: Temporarily timeout users using Discord's native timeout feature.

### 🎟️ Ticket System
- **Fully Configurable**: Set the category, log channel, and support role directly from Discord (no `.env` needed).
- **Interactive Panel**: Users open tickets via a persistent button and a modal to describe their request.
- **Private Channels**: Automatic creation of private channels where only the user, staff, and bot can interact.
- **Control Buttons**: Close the ticket with a single click.
- **Transcripts**: Generate and download HTML transcripts of the conversation.
- **Logs**: Automatic logging of ticket openings and closings in a dedicated channel.

### 🤖 AI Assistant
- **Groq Integration**: Fast and free AI responses powered by the Groq API.
- **Channel-Restricted**: The `/ask` command only works in a channel chosen by an admin.
- **Owner-Only Setup**: The API key is configured through a hidden, owner-only slash command.
- **Persistent Configuration**: The API key and channel are saved to the database and `.env` file.
- **Smart Responses**: Long answers are automatically split across multiple messages to respect Discord's character limit.

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
