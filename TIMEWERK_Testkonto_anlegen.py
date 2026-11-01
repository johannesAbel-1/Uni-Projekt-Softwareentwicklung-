#!/usr/bin/env python3
"""Lokales Professor-Testkonto für den vorhandenen TIMEWERK Python Prototyp.

ANLEITUNG
1. Diese Datei neben die vorhandene server.py kopieren.
2. TIMEWERK Server gegebenenfalls beenden.
3. Im Projektordner ausführen:
       python TIMEWERK_Testkonto_anlegen.py
4. Die angezeigten Zugangsdaten notieren.
5. Anwendung starten:
       python server.py
6. Im Browser http://127.0.0.1:8000 öffnen und normal anmelden.

Andere Dateinamen oder Datenbankpfade:
    python TIMEWERK_Testkonto_anlegen.py --server "Eingefügter Text.txt"
    python TIMEWERK_Testkonto_anlegen.py --db "C:/TIMEWERK/timewerk.sqlite3"

Das Konto wird erst beim Ausführen in der lokalen Datenbank angelegt.
Auf einem anderen Rechner sind eine eigene lokale Installation und dieses
Setup nötig. Eine Online-Version verwendet die Datenbank des Online-Servers.

Python 3.10+, nur Standardbibliothek. Nutzt init_db, connect und password_hash
des vorhandenen Servercodes; der HTTP Server wird beim Laden nicht gestartet.
Die Benutzeradresse lautet prof@timewerk.test und benötigt kein E Mail Postfach.
Ein zufälliges Passwort wird nur beim Anlegen angezeigt, nicht in eine Datei
geschrieben. In der Datenbank werden Salt und Hash gespeichert.
Ein vorhandenes Konto wird weder verändert noch mit Beispieldaten überschrieben.
Beispieldaten sind frei erfundene Lernziele, Aufgaben und Lernblöcke.
"""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import types

EMAIL = "prof@timewerk.test"
NAME = "Professor Testkonto"


def load_server(server_path, database=None):
    """Originalcode als Modul laden und den konfigurierten Datenbankpfad nutzen."""
    server_path = Path(server_path).expanduser().resolve()
    if not server_path.is_file():
        raise ValueError(
            f"Serverdatei nicht gefunden: {server_path}. "
            "Setup neben server.py ablegen oder --server angeben."
        )
    app = types.ModuleType("timewerk_account_setup")
    app.__file__ = str(server_path)
    exec(compile(server_path.read_text(encoding="utf-8-sig"),
                 str(server_path), "exec"), app.__dict__)
    for name in ("init_db", "connect", "password_hash", "DB"):
        if not hasattr(app, name):
            raise ValueError(f"Erwartete TIMEWERK Schnittstelle fehlt: {name}")
    # --db hat Vorrang. Ohne diesen Parameter gilt TIMEWERK_DB oder der
    # Standardpfad der geladenen server.py, genau wie beim normalen Appstart.
    app.DB = Path(database if database is not None else app.DB).expanduser().resolve()
    if not app.DB.parent.is_dir():
        raise ValueError(f"Datenbankordner fehlt: {app.DB.parent}")
    return app


def insert_examples(connection, user_id):
    """Nur für ein frisch erstelltes Konto; Einfügen in derselben Transaktion."""
    today = date.today()
    next_day = (today + timedelta(days=1)).isoformat()
    second_day = (today + timedelta(days=2)).isoformat()
    goals = [
        ("prof-sql", user_id, "[Beispiel] SQL Grundlagen",
         "Datenbanken", (today + timedelta(days=14)).isoformat(), 6.0, False, None),
        ("prof-uml", user_id, "[Beispiel] UML wiederholen",
         "Software Engineering", (today + timedelta(days=21)).isoformat(), 4.0, False, None),
    ]
    connection.executemany(
        "INSERT INTO goals "
        "(id,user_id,title,module,deadline,workload,done,achieved_at) "
        "VALUES (?,?,?,?,?,?,?,?)", goals,
    )
    connection.executemany(
        "INSERT INTO tasks (id,user_id,title,goal,date,done) VALUES (?,?,?,?,?,?)",
        [
            ("prof-aufgabe-1", user_id, "[Beispiel] SELECT und WHERE üben",
             "prof-sql", next_day, False),
            ("prof-aufgabe-2", user_id, "[Beispiel] Ein Klassendiagramm erstellen",
             "prof-uml", second_day, False),
        ],
    )
    connection.executemany(
        "INSERT INTO blocks (id,user_id,goal,date,time,minutes) VALUES (?,?,?,?,?,?)",
        [
            ("prof-block-1", user_id, "prof-sql", next_day, "10:00", 45),
            ("prof-block-2", user_id, "prof-uml", second_day, "11:00", 60),
        ],
    )
    connection.execute(
        "INSERT INTO planning (user_id,monthly,versions,plan) VALUES (?,?,?,?)",
        (user_id, json.dumps({today.strftime("%Y-%m"): 10}), "[]", "A"),
    )


def create_account(app, examples=True):
    """Konto und Beispiele atomar anlegen; bestehende Konten unverändert lassen.

    Rückgabe: neues Passwort oder None, falls das Konto bereits existiert.
    """
    app.init_db()
    with app.connect() as connection:
        # Gleiche Normalisierung wie bei der ursprünglichen Registrierung.
        existing = connection.execute(
            "SELECT id FROM users WHERE lower(trim(email))=?", (EMAIL,)
        ).fetchone()
        if existing is not None:
            return None
        password = secrets.token_urlsafe(18)  # 24 Zeichen; Server erlaubt 10–128.
        salt = secrets.token_hex(16)
        password_digest = app.password_hash(password, salt)
        cursor = connection.execute(
            "INSERT INTO users (email,name,salt,password_hash) VALUES (?,?,?,?)",
            (EMAIL, NAME, salt, password_digest),
        )
        if examples:
            insert_examples(connection, cursor.lastrowid)
        # Der Connection Kontext bestätigt beide Änderungen gemeinsam.
        # Bei einer Exception werden Konto und Beispiele zurückgerollt.
    return password


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--server", type=Path,
                        default=Path(__file__).with_name("server.py"))
    parser.add_argument("--db", type=Path,
                        help="Abweichender Datenbankpfad; auch beim Appstart verwenden")
    parser.add_argument("--ohne-beispieldaten", action="store_true",
                        help="Nur ein leeres Testkonto anlegen")
    args = parser.parse_args(argv)
    try:
        app = load_server(args.server, args.db)
        password = create_account(app, not args.ohne_beispieldaten)
    except (OSError, ValueError, TypeError, sqlite3.Error) as error:
        print(f"Testkonto konnte nicht angelegt werden: {error}", file=sys.stderr)
        return 1

    print(f"Datenbank: {app.DB}")
    if password is None:
        print(f"Das Testkonto {EMAIL} existiert bereits.")
        print("Passwort und vorhandene Lerndaten wurden nicht verändert.")
        print("Bitte die beim ersten Anlegen notierten Zugangsdaten verwenden.")
        return 0

    print("\nDas lokale Testkonto wurde angelegt.")
    print(f"E-Mail:   {EMAIL}")
    print(f"Passwort: {password}")
    print("Bitte das Passwort jetzt notieren; es wird nicht als Klartext gespeichert.")
    if not args.ohne_beispieldaten:
        print("Beispieldaten: 2 Lernziele, 2 Aufgaben, 2 Lernblöcke.")
    print("\nJetzt TIMEWERK mit derselben Datenbank starten und normal anmelden.")
    if args.db is not None:
        print("WICHTIG: Für den Appstart TIMEWERK_DB auf den oben gezeigten Pfad setzen.")
        print("PowerShell Beispiel:")
        print("$env:TIMEWERK_DB = '" + str(app.DB).replace("'", "''") + "'")
        print("python server.py")
    print("Standardadresse: http://127.0.0.1:8000")
    print("Das Konto hat normale Nutzerrechte für seine eigenen Lerndaten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
