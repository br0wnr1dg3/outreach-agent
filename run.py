#!/usr/bin/env python
"""Entry point for outreach CLI."""

# Load .env file before anything else
from dotenv import load_dotenv
load_dotenv()

from src.core.cli import main

if __name__ == "__main__":
    main()
