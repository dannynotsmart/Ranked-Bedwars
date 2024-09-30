from typing import Callable, TypeVar

import asqlite
import discord
import functools

T = TypeVar('T')

class DatabaseManager:
    def __init__(self, fp = "database.db"):
        """The database manager for the RBW bot's database, which is sqlite.

        Args:
            fp (str, optional): The filepath to the database file. Defaults to "database.db".
        """
        self.fp = fp

        self._cache = {}
        self._conn = None

    @property
    def cache(self) -> dict:
        """Stores database rows in a cache, for minimizing the amount of fetch calls to the database.

        Returns:
            dict: The cache.
        """
        return self._cache
    
    @property
    def conn(self) -> asqlite.Connection | None:
        """The connection object to the database.

        Returns:
            asqlite.Connection | None: The connection object to the database.
        """
        return self._conn
    
    async def connect(self) -> asqlite.Connection:
        """Connects to the database.

        Returns:
            asqlite.Connection: The connection object to the database.
        """
        if self._conn:
            return self.conn

        self._conn = await asqlite.connect(self.fp)

        with open("schema.sql", "r") as f:
            text = f.read()

        cur = await self.conn.cursor()

        for line in text.split(";"):
            await cur.execute(line)

        await cur.close()

        return self.conn
    
    def is_connected(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to ensure that there is a existing connection to the database.

        Args:
            func (Callable[..., T]): The function to wrap.

        Returns:
            Callable[..., T]: The wrapped function.
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            assert self.conn is not None, "Database connection is not established."
            return func(self, *args, **kwargs)
        return wrapper
    
    is_connected = staticmethod(is_connected)
    
    @is_connected
    async def close(self) -> None:
        """Closes the database connection."""
        await self.conn.close()

    @is_connected
    async def load_cache(self) -> dict:
        """Loads the cache with data from the database. This should ideally be called after connecting to the database.

        Returns:
            dict: The cache.
        """

        cur = await self.conn.cursor()

        guilds = await cur.execute("SELECT * FROM guilds;")
        guilds = await guilds.fetchall()

        # TODO: Optimize this function by calling only 4 select statements rather than N times

        for guild in guilds:
            guild_dict = {}

            for key in guild.keys():
                guild_dict[key] = guild[key]

            guild_dict["users"] = {}

            users = await cur.execute("SELECT * FROM users WHERE guild_id=?", (guild["guild_id"],))
            users = await users.fetchall()

            for user in users:
                user_dict = {}

                for key in user.keys():
                    user_dict[key] = user[key]

                guild_dict["users"][user["user_id"]] = user_dict

            guild_dict["matches"] = {}

            matches = await cur.execute("SELECT * FROM matches WHERE guild_id=?", (guild["guild_id"],))
            matches = await matches.fetchall()

            for match in matches:
                match_dict = {}

                for key in match.keys():
                    match_dict[key] = match[key]

                match_players = {}

                players = await cur.execute("SELECT * FROM match_players WHERE guild_id=? AND match_id=?", (guild["guild_id"], match["match_id"]))
                players = await players.fetchall()

                for player in players:
                    player_dict = {}

                    for key in player.keys():
                        player_dict[key] = player[key]

                    match_players[player["user_id"]] = player_dict

                match_dict["players"] = match_players

                guild_dict["matches"][match["match_id"]] = match_dict

            self.cache[guild["guild_id"]] = guild_dict

        await cur.close()

        return self.cache
    
    async def setup(self) -> None:
        """Helper method that automatically calls `connect` and `load_cache`.
        """
        await self.connect()
        await self.load_cache()

    @is_connected
    def get_guild(self, guild: discord.Guild) -> dict | None:
        """Returns the data for a given guild.

        Args:
            guild (discord.Guild): The guild.

        Returns:
            dict | None: The data from the cache. If not found, then returns `None`.
        """
        return self.cache.get(guild.id)
    
    @is_connected
    async def insert_guild(self, guild: discord.Guild) -> dict | None:
        """Inserts a row for the guild to the database. Returns `None` if the guild already exists.

        Args:
            guild (discord.Guild): The guild.

        Returns:
            dict | None: The row for the guild, which will have default values. If guild already exists in the database, returns `None`.
        """
        if self.get_guild(guild):
            return
        
        self.cache[guild.id] = {
            "guild_id": guild.id,
            "vc_queues_category": 0,
            "vc_matches_category": 0,
            "scorer_role_id": 0,
            "log_channel": 0,
            "users": {},
            "matches": {}
        }

        cur = await self.conn.cursor()

        await cur.execute("INSERT INTO guilds (guild_id) VALUES (?)", (guild.id,))
        await self.conn.commit()

        await cur.close()

        return self.get_guild(guild)
    
    @is_connected
    async def update_guild(self, guild: discord.Guild, *,
                           vc_queues_category: int | None = None,
                           vc_matches_category: int | None = None,
                           scorer_role_id: int | None = None,
                           log_channel: int | None = None) -> dict | None:
        """Updates the guild row. Pass in the necessary arguments for the columns that need to be updated.

        Args:
            guild (discord.Guild): The guild.
            vc_queues_category (int | None, optional): The ID for the VC queues category. Defaults to None.
            vc_matches_category (int | None, optional): The ID for the VC matches category. Defaults to None.
            scorer_role_id (int | None, optional): The role ID of the scorer. Defaults to None.
            log_channel (int | None, optional): The ID for the log channel. Defaults to None.

        Returns:
            dict | None: The column(s) that were modified.
        """
        await self.insert_guild(guild)

        args = {
            "vc_queues_category": vc_queues_category,
            "vc_matches_category": vc_matches_category,
            "scorer_role_id": scorer_role_id,
            "log_channel": log_channel
        }

        args = {k: v for k, v in args.items() if v is not None}

        if not args:
            return
        
        guild_dict = self.get_guild(guild)

        for k, v in args.items():
            guild_dict[k] = v

        set_clause = ', '.join([f"{k} = ?" for k in args.keys()])
        sql = f"UPDATE guilds SET {set_clause} WHERE guild_id = ?"

        values = tuple(args.values()) + (guild.id,)
        
        cur = await self.conn.cursor()

        await cur.execute(sql, values)
        await self.conn.commit()

        await cur.close()

        return args

    @is_connected
    async def get_user(self, member: discord.Member) -> dict | None:
        """Gets the user profile for a member.

        Args:
            member (discord.Member): The member. Note that this is NOT a `discord.User` object, as the member has to belong in a guild.

        Returns:
            dict | None: The data from the cache. If not found, then returns `None`.
        """
        guild = self.get_guild(member.guild) or await self.insert_guild(member.guild)

        return guild["users"].get(member.id)
    
    @is_connected
    async def insert_user(self, member: discord.Member, username: str) -> dict | None:
        """Inserts a row for the user to the database. Returns `None` if the user already exists.

        Args:
            member (discord.Member): The member.
            username (str): Their IGN / username.

        Returns:
            dict | None: The row for the user, which will have default values. If user already exists in the database, returns `None`.
        """
        user = await self.get_user(member)

        if user:
            return
        
        guild = self.get_guild(member.guild)

        guild["users"][member.id] = {
            "guild_id": member.guild.id,
            "user_id": member.id,
            "username": username,
            "elo": 0,
            "banned": 0,
            "wins": 0,
            "losses": 0
        }

        cur = await self.conn.cursor()

        await cur.execute("INSERT INTO users (guild_id, user_id, username) VALUES (?, ?, ?)", (member.guild.id, member.id, username))
        await self.conn.commit()

        await cur.close()

        return await self.get_user(member)
    
    @is_connected
    async def update_user(self, member: discord.Member, *,
                          username: str | None = None,
                          elo: int | None = None,
                          banned: int | None = None,
                          wins: int | None = None,
                          losses: int | None = None) -> dict | None:
        """Updates the user row. Pass in necessary arguments for the columns that need to be updated.

        Args:
            member (discord.Member): The member.
            username (str | None, optional): The username / IGN. Defaults to None.
            elo (int | None, optional): Their ranked ELO. Defaults to None.
            banned (int | None, optional): Whether they are queue banned. 0 means false, 1 means true. Defaults to None.
            wins (int | None, optional): Amount of wins. Defaults to None.
            losses (int | None, optional): Amount of losses. Defaults to None.

        Returns:
            dict | None: The column(s) that were modified.
        """
        user = await self.get_user(member)

        if not user:
            return
        
        args = {
            "username": username,
            "elo": elo,
            "banned": banned,
            "wins": wins,
            "losses": losses
        }

        args = {k: v for k, v in args.items() if v is not None}

        if not args:
            return
        
        for k, v in args.items():
            user[k] = v

        set_clause = ', '.join([f"{k} = ?" for k in args.keys()])
        sql = f"UPDATE users SET {set_clause} WHERE guild_id=? AND user_id=?"

        values = tuple(args.values()) + (member.guild.id, member.id)
        
        cur = await self.conn.cursor()

        await cur.execute(sql, values)
        await self.conn.commit()

        await cur.close()

        return args
