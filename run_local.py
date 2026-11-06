"""Локальный запуск: пароль запрашивается без отображения и не сохраняется."""

import getpass
import os

import uvicorn


if __name__ == "__main__":
    if "PGPASSWORD" not in os.environ:
        print("Введите пароль PostgreSQL. Он не отображается и не сохраняется в файле.")
        print("Если настроен pgpass, оставьте строку пустой и нажмите Enter.")
        password = getpass.getpass("Пароль PostgreSQL: ")
        if password:
            os.environ["PGPASSWORD"] = password
    print("RemI AI: http://127.0.0.1:8000")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
