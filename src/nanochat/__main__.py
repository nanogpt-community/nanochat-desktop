"""Entry point for NanoChat Desktop."""

import sys


def main() -> int:
    """Main entry point."""
    from nanochat.application import NanoChatApplication
    app = NanoChatApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
