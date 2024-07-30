import logging
from config.loader import load_config
from config.logging_setup import setup_logging
from src.classes.threadManager import ThreadManager

def main():
    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Fire Alarm Control Panel Monitor")

    # Initialize and start ThreadManager
    thread_manager = ThreadManager(config)
    thread_manager.start()

    try:
        # Keep the main thread alive
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    finally:
        thread_manager.stop()
        logger.info("Application shut down complete.")

if __name__ == "__main__":
    main()