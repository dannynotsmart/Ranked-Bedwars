CREATE TABLE IF NOT EXISTS guilds(
    guild_id INTEGER NOT NULL,
    vc_queues_category INTEGER NOT NULL DEFAULT 0,
    vc_matches_category INTEGER NOT NULL DEFAULT 0,
    scorer_role_id INTEGER NOT NULL DEFAULT 0,
    log_channel INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS users(
    guild_id INTEGER NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    elo INTEGER NOT NULL DEFAULT 0,
    banned INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS matches(
    guild_id INTEGER NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    vc_id INTEGER NOT NULL,
    textchannel_id INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    ongoing INTEGER NOT NULL DEFAULT 1,
    team1_score INTEGER NOT NULL DEFAULT 0,
    team2_score INTEGER NOT NULL DEFAULT 0,
    scorer INTEGER NOT NULL DEFAULT 0,
    end_time INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(guild_id, match_id)
);

CREATE TABLE IF NOT EXISTS match_players(
    guild_id INTEGER NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    team INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(guild_id, match_id, user_id)
);