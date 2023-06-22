import sqlite3
from typing import Optional, overload, cast


class DB:
    con: sqlite3.Connection
    cur: sqlite3.Cursor

    def __init__(self, path: str) -> None:
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS KeyVal (Key TEXT, Value TEXT)")

    @overload
    def get(self, key: str) -> Optional[str]:
        ...

    @overload
    def get(self, key: str, default: None) -> Optional[str]:
        ...

    @overload
    def get(self, key: str, default: str) -> str:
        ...

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if not isinstance(key, str):
            raise TypeError("Only string keys are allowed")

        query_result = self.cur.execute("SELECT Value FROM KeyVal WHERE Key=?", (key,))

        if val := query_result.fetchone():
            return cast(str, val[0])
        else:
            return default

    def __getitem__(self, key: str) -> str:
        val = self.get(key)

        if val is None:
            raise KeyError(key)
        else:
            return val

    def set(self, key: str, value: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Only string keys are allowed")

        if not isinstance(value, str):
            raise TypeError("Only string values are allowed")

        exists = self.cur.execute("SELECT EXISTS(SELECT 1 FROM KeyVal WHERE Key=?)", (key,))

        if exists.fetchone()[0]:
            self.cur.execute("UPDATE KeyVal SET Value = ? WHERE Key=?", (value, key))
        else:
            self.cur.execute("INSERT INTO KeyVal VALUES(?,?)", (key, value))

        self.con.commit()

    def __setitem__(self, key: str, value: str) -> None:
        self.set(key, value)

    def pop(self, key: str, default: Optional[str] = None) -> str:
        if not isinstance(key, str):
            raise TypeError("Only string keys are allowed")

        item = self.get(key)

        if item is not None:
            self.cur.execute("DELETE FROM KeyVal WHERE Key=?", (key,))
            self.con.commit()
            return item
        else:
            if default is None:
                raise KeyError(key)
            else:
                return default

    def __delitem__(self, key: str) -> None:
        self.pop(key)
