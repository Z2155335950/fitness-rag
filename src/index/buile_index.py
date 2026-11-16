"""Backward-compatible entry point for the old misspelled module name."""

from src.index.build_index import build

__all__ = ["build"]


if __name__ == "__main__":
    build()
