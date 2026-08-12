"""Development-server entrypoint for the local Card Maker spike."""

from __future__ import annotations

import logging

from cardmaker.app import create_app
from cardmaker.config import Settings


def main() -> None:
    settings = Settings.from_environ()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger(__name__).warning(
        "cardmaker_started bind=%s port=%d server=werkzeug-development",
        settings.http_bind,
        settings.http_port,
    )
    create_app(settings).run(
        host=settings.http_bind,
        port=settings.http_port,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
