import os
import sqlite3
import datetime
import time
from typing import Any, Dict, Generic, List, Tuple, TypeVar, Union, LiteralString, Type, Optional

from utils.database import structs

T = TypeVar("T")
MySQLValue = Union[int, float, str, bytes, datetime.datetime, None]
PVal = Union[MySQLValue, Tuple[MySQLValue], Dict[str, MySQLValue], T]

class database:
    def __init__(self, debug: bool = False) -> None:
        if not os.path.exists("production.db"):
            print("Waiting ... please upload production.db ...")
            while not os.path.exists("production.db"):
                time.sleep(2)

        if debug: self.con = sqlite3.connect("testing.db", check_same_thread=False)
        else: self.con = sqlite3.connect("production.db", check_same_thread=False)
        
        self.con.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.con.cursor()
        self.debug = debug

    def commit(self) -> None:
        self.con.commit()

    def close(self) -> None:
        self.cursor.close()
        self.con.close()

class table(Generic[T]):
    def __init__(self,
        db: database,
        name: LiteralString,
        pkey: Union[LiteralString, Tuple[LiteralString]],
        data_cls: Type[T]
    ) -> None:
        self.db = db
        self.name = name
        self.data_cls = data_cls

        self.db.cursor.execute(f"PRAGMA table_info({name})")
        self.fields = tuple(row[1] for row in self.db.cursor.fetchall())
        self.pkey = pkey if isinstance(pkey, tuple) else (pkey,)

        self._where = " AND ".join(f"{key} = ?" for key in self.pkey)
        self._struct = "(`" + "`, `".join(self.fields) + "`)"
        self._ph = "(" + ", ".join(("?",) * len(self.fields)) + ")"

    def _parse_keys(self, pkv: PVal) -> Tuple[MySQLValue]:
        if isinstance(pkv, tuple):
            return tuple(pkv[i] for i in range(len(self.pkey)))
        if isinstance(pkv, dict):
            return tuple(pkv[k] for k in self.pkey)
        if isinstance(pkv, self.data_cls):
            return tuple(getattr(pkv, k) for k in self.pkey)
        return (pkv,)
    
    def _parse_data(self, *args, **kwargs) -> Tuple[MySQLValue]:
        if kwargs: return tuple(kwargs[f] for f in self.fields)
        if args:
            if len(args) == 1:
                if isinstance(args[0], (tuple, list)):
                    return tuple(args[0])
                elif isinstance(args[0], dict):
                    return tuple(args[0][f] for f in self.fields)
            return tuple(args)

    def fetchall(self, pkv: PVal) -> List[T]:
        query = f"SELECT * FROM {self.name} WHERE {self._where}"
        self.db.cursor.execute(query, self._parse_keys(pkv))
        return [self.parse(*row) for row in self.db.cursor.fetchall()]

    def fetchone(self, pkv: PVal) -> Optional[T]:
        query = f"SELECT * FROM {self.name} WHERE {self._where}"
        self.db.cursor.execute(query, self._parse_keys(pkv))
        return self.parse(self.db.cursor.fetchone())

    def fetchmany(self, pkv: PVal, limit: int) -> List[T]:
        query = f"SELECT * FROM {self.name} WHERE {self._where} LIMIT {limit}"
        self.db.cursor.execute(query, self._parse_keys(pkv))
        return [self.parse(*row) for row in self.db.cursor.fetchall()]

    def insert_record(self, record: T) -> None:
        self.db.cursor.execute(
            f"INSERT INTO {self.name} {self._struct} VALUES {self._ph}",
            tuple(getattr(record, f) for f in self.fields)
        )
        self.db.commit()

    def insert(self, *args: Union[MySQLValue, Tuple[MySQLValue]], **kwargs: Dict[str, MySQLValue]) -> None:
        self.db.cursor.execute(
            f"INSERT INTO {self.name} {self._struct} VALUES {self._ph}",
            self._parse_data(*args, **kwargs)
        )
        self.db.commit()

    def update_record(self, record: T) -> None:
        update_keys = ", ".join(f"{key} = ?" for key in self.fields)
        self.db.cursor.execute(
            f"UPDATE {self.name} SET {update_keys} WHERE {self._where}",
            tuple(getattr(record, f) for f in self.fields) + self._parse_keys(record)
        )
        self.db.commit()

    def update(self, *args: Union[MySQLValue, Tuple[MySQLValue]], **kwargs: Dict[str, MySQLValue]) -> None:
        update_keys = ", ".join(f"{key} = ?" for key in self.fields)
        update_data = self._parse_data(*args, **kwargs)
        self.db.cursor.execute(
            f"UPDATE {self.name} SET {update_keys} WHERE {self._where}",
            update_data + self._parse_keys(update_data)
        )
        self.db.commit()

    def delete(self, pval: PVal) -> None:
        self.db.cursor.execute(
            f"DELETE FROM {self.name} WHERE {self._where}",
            self._parse_keys(pval)
        )
        self.db.commit()

    def parse(self, *args: Union[Tuple[MySQLValue], MySQLValue], **kwargs: MySQLValue) -> Union[T, None]:
        if kwargs: return self.data_cls(**kwargs)
        if args:
            if args[0] is None:
                return None
            if isinstance(args[0], tuple):
                return self.data_cls(*args[0])
            return self.data_cls(*args)