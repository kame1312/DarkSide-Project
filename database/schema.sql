CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `secnews_channels` (
  `server_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `secnews_last_seen` (
  `feed_url` varchar(255) NOT NULL PRIMARY KEY,
  `entry_id` varchar(500) NOT NULL
);

CREATE TABLE IF NOT EXISTS `tickets` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `guild_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL UNIQUE,
  `user_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `closed` INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS `ticket_config` (
  `guild_id` varchar(20) NOT NULL PRIMARY KEY,
  `category_id` varchar(20),
  `log_channel_id` varchar(20),
  `support_role_id` varchar(20)
);