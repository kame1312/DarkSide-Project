# DarkSide Protect

A multifunctional Discord bot built with `discord.py`. Moderation, tickets, cybersecurity news, GitHub push notifications, an AI assistant and more — all configurable from a modern interactive dashboard.

## Features

### 🎛️ Interactive Dashboard
The `/dashboard` command opens an ephemeral panel that lets you configure every feature without typing a single command. Every setting is stored in the database and reloaded when you reopen the panel — modify the values, then click **Save**.

- **Tickets**: category, log channel, support role, editable panel message.
- **Security News**: target channel, manual test trigger.
- **GitWatch**: target channel, manual test, disable.
- **Welcome**: channel, message (with placeholders), live preview.
- **Suggestions**: submit an idea straight to the owner.
- **Help** and **Close** buttons.

Prefix commands remain available as fallback for every feature.

### 🛡️ Moderation
- Kick / Ban / Hackban with reasons and DM notifications.
- Nickname management.
- Warning system (add / remove / list) backed by SQLite.
- Purge and archive messages.
- Mute / Unmute via Discord's native timeout.
- Welcome system with placeholders: `{user}`, `{user_name}`, `{user_display}`, `{guild}`, `{member_count}`.

### 🎟️ Tickets
- Private channels created on demand via a persistent button + modal.
- Support role automatically granted access.
- **Close** and **Transcript** buttons in every ticket.
- HTML transcripts and logging to a dedicated channel.

### 💡 Suggestions
- `/suggest` opens a modal.
- Suggestions are delivered as rich embeds to a channel set once by the owner via `/setup_suggestions`.

### 🤖 AI Assistant
- Powered by Groq, configured via `GROQ_API_KEY` in `.env`.
- Triggered by mentioning the bot or replying to one of its messages.
- Context-aware (reads the last 60 messages) and multi-user aware — each message is tagged with its author's name.
- Automatic model fallback if a model becomes unavailable or rate-limited.
- Long answers are split across multiple messages.

### 📰 Security News
- Fetches 30+ cybersecurity RSS feeds (The Hacker News, BleepingComputer, Krebs on Security, ANSSI, CERT-FR...).
- Channel configurable from the dashboard.
- Manual test trigger.

### 🔔 GitWatch
- Polls the GitHub Atom feed of a repository and posts every new commit.
- Persistent state across restarts — no commit is missed or duplicated.
- Configurable from the dashboard.
- No token required for public repositories.

### ⚙️ General
- `/help`, `/serverinfo`, `/ping`, `/invite`.

### 👑 Owner
- Cog management (`load` / `unload` / `reload`), slash command sync / unsync.
- `say`, `embed`, `broadcast`.
- `/setup_suggestions` to define the global suggestion channel.
- `/servers`, `/botinfo`, `/shutdown`.

## Commands

### Dashboard
| Command | Description | Permissions |
|---|---|---|
| `/dashboard` | Open the interactive configuration dashboard. | Administrator |
| `/suggest` | Submit a suggestion to the bot owner. | Everyone |

### Moderation
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

### Tickets
> Configure from the `/dashboard`. Prefix commands remain as fallback.

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

### Security News
> Configure from the `/dashboard`. Prefix commands remain as fallback.

| Command | Description | Permissions |
|---|---|---|
| `!secnews setchannel` | Set the channel where security news will be posted. | Administrator |
| `!secnews test` | Force an immediate check of all feeds. | Administrator |

### GitWatch
> Configure from the `/dashboard`. Prefix commands remain as fallback.

| Command | Description | Permissions |
|---|---|---|
| `!gitwatch setchannel <channel>` | Set the channel where git push notifications are posted. | Owner |
| `!gitwatch disable` | Disable git push notifications. | Owner |
| `!gitwatch test` | Force an immediate check of the GitHub feed. | Owner |

### Welcome
> Configure from the `/dashboard`. Prefix commands remain as fallback.

| Command | Description | Permissions |
|---|---|---|
| `!welcome channel` | Set the welcome channel. | Manage Server |
| `!welcome message` | Set the welcome message. | Manage Server |
| `!welcome test` | Send a preview of the welcome message. | Manage Server |
| `!welcome disable` | Disable the welcome message. | Manage Server |

### General
| Command | Description |
|---|---|
| `/help` | List all commands the bot has loaded. |
| `/serverinfo` | Get information about the current server. |
| `/ping` | Check the bot's latency. |
| `/invite` | Get the bot's invite link. |

### Owner
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

## License
This project is licensed under the Apache License 2.0 — see the `LICENSE.md` file for details.