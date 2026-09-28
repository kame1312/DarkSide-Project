# DarkSide Protect

A multifunctional Discord bot built with `discord.py` that provides robust moderation tools, comprehensive server information, owner utilities, an automated cybersecurity news feed system, an integrated AI assistant powered by Groq, a GitHub push notification watcher, and a fully configurable ticket system — all manageable through a modern interactive dashboard.

## Features

### 🎛️ Interactive Dashboard
- **Central Configuration Hub**: The `/dashboard` command opens an ephemeral interactive panel with buttons to configure every feature of the bot.
- **No Slash Commands Needed**: Tickets, Security News, GitWatch, and Welcome systems are now configurable entirely from the dashboard — no need to type any commands.
- **Saved Configurations**: Every setting is stored in the database and automatically re-loaded when you re-open the dashboard.
- **Confirmation Workflow**: Modify the desired values, then click **Save** to apply the changes.
- **Editable Ticket Panel**: Customize the title and description of the ticket panel directly from the dashboard.
- **Editable Welcome Message**: Set, edit, and preview the welcome message with live placeholders.
- **Help Button**: Access the full command list from within the dashboard.
- **Close Button**: Dismiss the dashboard when you're done.

### 🛡️ Moderation
- **Kick / Ban / Hackban**: Manage members with detailed reasons and DM notifications.
- **Nickname Management**: Change or reset member nicknames.
- **Warning System**: Add, remove, and list warnings for users (backed by SQLite).
- **Purge**: Bulk delete messages from a channel.
- **Archive**: Save the last messages of a channel into a text file.
- **Mute / Unmute**: Temporarily timeout users using Discord's native timeout feature.
- **Welcome System**: Configurable welcome messages with placeholders (`{user}`, `{user_name}`, `{user_display}`, `{guild}`, `{member_count}`), live preview, and toggle — now fully configurable via the dashboard.

### 🎟️ Ticket System
- **Fully Configurable**: Set the category, log channel, and support role directly from the dashboard (no commands needed).
- **Editable Panel**: Customize the panel title and description from the dashboard.
- **Interactive Panel**: Users open tickets via a persistent button and a modal to describe their request.
- **Private Channels**: Automatic creation of private channels where only the user, staff, and bot can interact.
- **Control Buttons**: Close the ticket with a single click, or generate an HTML transcript on demand.
- **Transcripts**: Generate and download HTML transcripts of the conversation.
- **Logs**: Automatic logging of ticket openings and closings in a dedicated channel.

### 💡 Suggestions
- **Public Command**: Any user can submit a suggestion using the `/suggest` command.
- **Gateway System**: Suggestions are sent directly to the bot owner in a private, dedicated channel — no need to be on a support server.
- **Owner-Configurable Channel**: The destination channel is set once by the owner with the `/setup_suggestions` command.
- **Structured Modal**: Users fill in a title and a detailed description before submission.
- **Rich Embed**: Each suggestion is delivered as a clean embed including the author's username, ID, avatar, and originating server.

### 🤖 AI Assistant
- **Groq Integration**: Fast and free AI responses powered by the Groq API.
- **Mention Trigger**: Just ping the bot with your question to get an answer.
- **Reply Trigger**: You can also reply to any of the bot's messages to continue the conversation.
- **Context-Aware**: The bot reads the last 60 messages of the channel to give relevant answers.
- **Multi-User Awareness**: Each message is tagged with its author's display name, so the AI knows who said what and can address the right person.
- **Automatic Model Fallback**: If a Groq model becomes unavailable, hits a rate limit, or is deprecated, the bot automatically switches to the next available model (from a priority list) without any intervention.
- **Dynamic Model Detection**: On startup, the bot queries the Groq API to select the best available model from its fallback list.
- **Environment Variable Configuration**: The API key is set directly in the `.env` file as `GROQ_API_KEY`.
- **Smart Responses**: Long answers are automatically split across multiple messages to respect Discord's character limit.

### 📰 Security News
- Automated RSS feed fetching from over 27 cybersecurity sources (The Hacker News, BleepingComputer, Krebs on Security, etc.).
- Configurable channel directly from the dashboard.
- Manual test trigger from the dashboard for immediate checks.

### 🔔 Git Watch
- **Automatic Push Notifications**: Polls the GitHub Atom feed of the configured repository and posts every new commit to a dedicated channel.
- **Configurable Channel**: Set the target channel from the dashboard.
- **Persistent State**: Remembers the last seen commit across restarts, so no commit is ever missed or duplicated.
- **Manual Test**: Force an immediate check of the feed from the dashboard.
- **No Token Required**: Works out of the box for public repositories without any GitHub token or webhook setup.

### ⚙️ General
- **Help**: Dynamically generated help menu listing all available commands. Also available via the dashboard's Help button.
- **Server Info**: Detailed statistics about the current server.
- **Ping**: Check the bot's latency.
- **Invite**: Get the bot's OAuth2 invite link.

### 👑 Owner
- **Cog Management**: Load, unload, and reload extensions on the fly.
- **Sync / Unsync**: Manage Discord slash commands synchronization.
- **Say / Embed**: Make the bot send custom messages.
- **Broadcast**: Send a message to every server the bot is in.
- **Setup Suggestions**: Define the global channel that receives user suggestions.
- **Shutdown**: Safely shut down the bot.
- **Bot Info**: Display real-time CPU usage, RAM consumption, uptime, and system information.
- **Server List**: List every server the bot is in, with an invite link for each.

## Commands

### 🎛️ Dashboard
| Command | Description | Permissions |
|---|---|---|
| `/dashboard` | Open the interactive configuration dashboard. | Administrator |
| `/suggest` | Submit a suggestion to the bot owner. | Everyone |

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

> 💡 The **Welcome** system is now configured via the `/dashboard` (prefix commands still available as fallback: `!welcome channel`, `!welcome message`, `!welcome test`, `!welcome disable`).

### 🎟️ Ticket System
> 💡 The ticket system is now configured via the `/dashboard`. Prefix commands still exist as fallback.

| Command | Description | Permissions |
|---|---|---|
| `!ticket_config` | Show the current ticket configuration. | Administrator |
| `!ticket_config category` | Set the category where tickets are created. | Administrator |
| `!ticket_config logs` | Set the channel where ticket logs are sent. | Administrator |
| `!ticket_config support` | Set the role that can see and manage tickets. | Administrator |
| `!ticket_config reset` | Reset the ticket configuration. | Administrator |
| `!ticket_panel` | Post the ticket panel in the current channel. | Administrator |
| `/ticket_close` | Close the current ticket. | Manage Channels |
| `/ticket_add` | Add a member to the current ticket. | Manage Channels |
| `/ticket_remove` | Remove a member from the current ticket. | Manage Channels |

### 💡 Suggestions
| Command | Description | Permissions |
|---|---|---|
| `/suggest` | Submit a suggestion to the bot owner via a private modal. | Everyone |

### 🤖 AI Assistant
**Set your API key in your `.env` file** as `GROQ_API_KEY`.

To use the AI, simply **ping the bot** with your question, or **reply to one of its messages**. The bot reads the last 60 messages of the channel to keep the conversation coherent, and distinguishes between all participants so it can address the right person.

If a Groq model becomes unavailable or rate-limited, the bot automatically falls back to the next available model from a built-in priority list.

### 📰 Security News
> 💡 Now configured via the `/dashboard`. Prefix commands still available as fallback.

| Command | Description | Permissions |
|---|---|---|
| `!secnews setchannel` | Set the channel where security news will be posted. | Administrator |
| `!secnews test` | Force an immediate check of all feeds. | Administrator |

### 🔔 Git Watch
> 💡 Now configured via the `/dashboard`. Prefix commands still available as fallback.

| Command | Description | Permissions |
|---|---|---|
| `!gitwatch setchannel <channel>` | Set the channel where git push notifications are posted. | Owner |
| `!gitwatch disable` | Disable git push notifications. | Owner |
| `!gitwatch test` | Force an immediate check of the GitHub feed. | Owner |

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
| `broadcast <message>` | Send a message to every server the bot is in. |
| `setup_suggestions <channel>` | Set the global channel that receives user suggestions. |
| `servers` | List all servers the bot is in, with an invite link for each. |
| `botinfo` | Display CPU, RAM, uptime, and system info. |
| `shutdown` | Shut down the bot. |

# LICENSE
This project is licensed under the Apache License 2.0 - see the LICENSE.md file for details.