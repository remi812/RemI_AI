import os

import psycopg
from psycopg.rows import dict_row


def open_database():
    return psycopg.connect(host=os.getenv("PGHOST", "127.0.0.1"), port=os.getenv("PGPORT", "5432"),
                           dbname=os.getenv("PGDATABASE", "RemI_AI"), user=os.getenv("PGUSER", "postgres"),
                           options="-c search_path=remi_project,pg_catalog", connect_timeout=3, row_factory=dict_row)

