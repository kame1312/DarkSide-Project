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