import sqlite3
from typing import Optional, overload, cast


class DB:
    con: sqlite3.Connection
    cur: sqlite3.Cursor

    def __init__(self, path: str) -> None:
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS KeyVal (Key TEXT PRIMARY KEY, Value TEXT)")

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

    def set(self, key: str, value: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Only string keys are allowed")

        if not isinstance(value, str):
            raise TypeError("Only string values are allowed")

        self.cur.execute("INSERT OR REPLACE INTO KeyVal (Key, Value) VALUES (?, ?)", (key, value))
        self.con.commit()

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

    def keys(self) -> list[str]:
        keys_in_db = self.cur.execute("SELECT Key FROM KeyVal")
        return [cast(str, x[0]) for x in keys_in_db.fetchall()]

    def values(self) -> list[str]:
        values_in_db = self.cur.execute("SELECT Value FROM KeyVal")
        return [cast(str, x[0]) for x in values_in_db.fetchall()]

    def items(self) -> list[tuple[str, str]]:
        kv_in_db = self.cur.execute("SELECT Key, Value FROM KeyVal")
        return [cast(tuple[str, str], x) for x in kv_in_db.fetchall()]

    def clear(self) -> None:
        self.cur.execute("DELETE FROM KeyVal")
        self.con.commit()

    def __getitem__(self, key: str) -> str:
        val = self.get(key)

        if val is None:
            raise KeyError(key)
        else:
            return val

    def __setitem__(self, key: str, value: str) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        self.pop(key)

    def __contains__(self, key: str) -> bool:
        exists = self.cur.execute("SELECT EXISTS(SELECT 1 FROM KeyVal WHERE Key=?)", (key,))
        return exists.fetchone()[0] == 1

    def __len__(self) -> int:
        size = self.cur.execute("SELECT COUNT(*) FROM KeyVal")
        return cast(int, size.fetchone()[0])

    def __del__(self) -> None:
        self.con.close()
