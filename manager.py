from typing import Callable, TypeVar
import asqlite
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
    
