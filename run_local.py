"""Локальный запуск с явно выбранной базой PostgreSQL."""
import argparse
import getpass
import os
import socket


import uvicorn

from app.operations import readiness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Выделенная база с суффиксом _demo")
    parser.add_argument("--port", type=int, default=os.getenv("REMI_HTTP_PORT", "8019"))
    parser.add_argument("--ask-password", action="store_true", help="Запросить пароль PostgreSQL в терминале")
    args = parser.parse_args()
    database = os.getenv("PGDATABASE", "")
    if not database:
        parser.error("Задайте PGDATABASE для выбранного стенда.")
    if args.test != database.endswith("_demo"):
        parser.error("Для --test выберите базу *_demo. Для обычного запуска укажите обычную базу.")
    if not 1 <= args.port <= 65535:
        parser.error("Порт должен быть в диапазоне 1–65535.")
    if args.ask_password:
        os.environ["PGPASSWORD"] = getpass.getpass("Пароль PostgreSQL: ")
    host = "127.0.0.1"
    with socket.socket() as listener:
        try:
            listener.bind((host, args.port))
            listener.listen()
        except OSError:
            parser.exit(1, f"Не удалось занять {host}:{args.port}. Проверьте запущенный сервер или задайте --port.\n")
        state = readiness()
        if not all(state.values()):
            missing = ", ".join(key for key,value in state.items() if not value)
            parser.exit(1, f"Стенд пока не готов ({missing}). Проверьте подключение и выполните init или migrate по инструкции.\n")
        print(f"RemI AI · {'тестовый' if args.test else 'обычный'} режим · http://{host}:{args.port}/", flush=True)
        uvicorn.Server(uvicorn.Config("app.main:app", host=host, port=args.port)).run(sockets=[listener])


if __name__ == "__main__":
    main()
