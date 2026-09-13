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
- **Welcome System**: Configurable welcome messages with placeholders (`{user}`, `{user_name}`, `{user_display}`, `{guild}`, `{member_count}`), live preview, and toggle.

### 🎟️ Ticket System
- **Fully Configurable**: Set the category, log channel, and support role directly from Discord (no `.env` needed).
- **Interactive Panel**: Users open tickets via a persistent button and a modal to describe their request.
- **Private Channels**: Automatic creation of private channels where only the user, staff, and bot can interact.
- **Control Buttons**: Close the ticket with a single click, or generate an HTML transcript on demand.
- **Transcripts**: Generate and download HTML transcripts of the conversation.
- **Logs**: Automatic logging of ticket openings and closings in a dedicated channel.

### 🤖 AI Assistant
- **Groq Integration**: Fast and free AI responses powered by the Groq API.
- **Mention Trigger**: Just ping the bot with your question to get an answer.
- **Reply Trigger**: You can also reply to any of the bot's messages to continue the conversation.
- **Context-Aware**: The bot reads the last 30 messages of the channel to give relevant answers.
- **Owner-Only Setup**: The API key is configured through a hidden, owner-only slash command.
- **Persistent Configuration**: The API key is saved to the `.env` file.
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

## Commands

### 🛡️ Moderation
| Command | Description | Permissions |
|---|---|---|
| `/kick` | Kick a user out of the server. | Kick Members |
| `/ban` | Ban a user from the server. | Ban Members |
| `/hackban` | Ban a user by ID without them being in the server. | Ban Members |
| `/nick` | Change a user's nickname. | Manage Nicknames |
| `/mute` | Temporarily timeout a user. | Moderate Members |
| `/unmute` | Remove a timeout from a user. | Moderate Members |
| `/purge` | Delete a number of messages. | Manage Messages |
| `/archive` | Save the last messages of a channel to a file. | Manage Messages |
| `/warning add` | Add a warning to a user. | Manage Messages |
| `/warning remove` | Remove a warning from a user. | Manage Messages |
| `/warning list` | List all warnings of a user. | Manage Messages |
| `/welcome channel` | Set the welcome channel. | Manage Server |
| `/welcome message` | Set the welcome message (supports placeholders). | Manage Server |
| `/welcome test` | Send a preview of the welcome message. | Manage Server |
| `/welcome disable` | Disable the welcome message. | Manage Server |

### 🎟️ Ticket System
| Command | Description | Permissions |
|---|---|---|
| `/ticket_config` | Show the current ticket configuration. | Administrator |
| `/ticket_config category` | Set the category where tickets are created. | Administrator |
| `/ticket_config logs` | Set the channel where ticket logs are sent. | Administrator |
| `/ticket_config support` | Set the role that can see and manage tickets. | Administrator |
| `/ticket_config reset` | Reset the ticket configuration. | Administrator |
| `/ticket_panel` | Post the ticket panel in the current channel. | Administrator |
| `/ticket_close` | Close the current ticket. | Manage Channels |
| `/ticket_add` | Add a member to the current ticket. | Manage Channels |
| `/ticket_remove` | Remove a member from the current ticket. | Manage Channels |

### 🤖 AI Assistant
| Command | Description | Permissions |
|---|---|---|
| `/setup_groq` | Configure the Groq API key. | Bot Owner |

To use the AI, simply **ping the bot** with your question, or **reply to one of its messages**. The bot reads the last 30 messages of the channel to keep the conversation coherent.

### 📰 Security News
| Command | Description | Permissions |
|---|---|---|
| `secnews setchannel` | Set the channel where security news will be posted. | Administrator |
| `secnews test` | Force an immediate check of all feeds. | Administrator |

### ⚙️ General
| Command | Description |
|---|---|
| `/help` | List all commands the bot has loaded. |
| `/serverinfo` | Get information about the current server. |
| `/ping` | Check the bot's latency. |
| `/invite` | Get the bot's invite link. |

### 👑 Owner
| Command | Description |
|---|---|
| `sync <scope>` | Synchronize slash commands globally or per guild. |
| `unsync <scope>` | Unsynchronize slash commands. |
| `load <cog>` | Load a cog. |
| `unload <cog>` | Unload a cog. |
| `reload <cog>` | Reload a cog. |
| `say <message>` | Make the bot say something. |
| `embed <message>` | Make the bot send an embed. |
| `botinfo` | Display CPU, RAM, uptime, and system info. |
| `shutdown` | Shut down the bot. |

# LICENSE
This project is licensed under the Apache License 2.0 - see the LICENSE.md file for details.