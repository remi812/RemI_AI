import os

import psycopg
from psycopg.rows import dict_row


def open_database():
    database = os.getenv("PGDATABASE")
    if not database or not os.getenv("PGUSER"):
        raise psycopg.OperationalError("Укажите PGUSER и PGDATABASE, чтобы выбрать базу RemI AI.")
    return psycopg.connect(host=os.getenv("PGHOST", "127.0.0.1"), port=os.getenv("PGPORT", "5432"),
                           dbname=database, user=os.environ["PGUSER"],
                           options="-c search_path=remi_project,pg_catalog -c statement_timeout=10000 -c lock_timeout=4000", connect_timeout=3, row_factory=dict_row)

