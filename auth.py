"""Authentication and user-management helpers."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from database import hash_password


@dataclass
class User:
    id: int
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def login(conn: sqlite3.Connection, username: str, password: str) -> User | None:
    row = conn.execute(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        return None
    if row["password_hash"] != hash_password(password):
        return None
    return User(id=row["id"], username=row["username"], role=row["role"])


def create_user(conn: sqlite3.Connection, username: str, password: str, role: str) -> int:
    if role not in ("admin", "cashier"):
        raise ValueError("role must be 'admin' or 'cashier'")
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, hash_password(password), role),
    )
    conn.commit()
    return cur.lastrowid


def delete_user(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()


def change_password(conn: sqlite3.Connection, user_id: int, new_password: str) -> None:
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(new_password), user_id),
    )
    conn.commit()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, username, role FROM users ORDER BY username").fetchall()
