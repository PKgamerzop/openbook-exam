"""Create development-only lecturer and student accounts without default passwords."""

from getpass import getpass

from app.access import password_hash
from app.db import get_engine
from app.store import one


def main():
    with get_engine().begin() as db:
        for username, role in [("lecturer", "lecturer"), ("student", "student")]:
            if one(db, "SELECT id FROM account WHERE username=:u", u=username):
                continue
            password = getpass(
                f"New local password for {username} (12-128 characters): "
            )
            if not 12 <= len(password) <= 128:
                raise ValueError("Password length must be 12-128 characters")
            one(
                db,
                """INSERT INTO account(username,role,password_hash)
                VALUES (:u,:r,:h) ON CONFLICT DO NOTHING RETURNING id""",
                u=username,
                r=role,
                h=password_hash(password),
            )


if __name__ == "__main__":
    main()
