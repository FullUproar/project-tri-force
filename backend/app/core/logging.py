import logging
import sys

from app.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    # Suppress noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


logger = logging.getLogger("triforce")
