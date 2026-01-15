"""Entry point for NanoChat Desktop."""

import sys
import logging

def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    
    from nanochat.application import NanoChatApplication
    app = NanoChatApplication()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
