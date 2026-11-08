"""Run the service locally: python -m app.server --db tasks.db --port 8000"""

from __future__ import annotations

import argparse
from wsgiref.simple_server import make_server

from .db import connect, init_db
from .seed import seed
from .web import make_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="tasks.db")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--seed", action="store_true", help="create the demo users")
    args = parser.parse_args()

    conn = connect(args.db)
    init_db(conn)
    if args.seed:
        seed(conn)
    with make_server("127.0.0.1", args.port, make_app(conn)) as server:
        print(f"serving on http://127.0.0.1:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
