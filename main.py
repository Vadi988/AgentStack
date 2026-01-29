from app.core.config.logging import configure_logging, get_logger


def main():
    configure_logging()
    logger = get_logger(__name__)
    logger.info("AgentStack started")


if __name__ == "__main__":
    main()
