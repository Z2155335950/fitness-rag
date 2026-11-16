from __future__ import annotations
from pathlib import Path

from src.config import PARSED_DIR

from .entity_linker import EntityLinker
from .router import route
from .schema import RoutedQuery


class QueryPipeline:
    def __init__(self, parsed_dir: str | Path = PARSED_DIR):
        self.linker = EntityLinker(parsed_dir)

    def process(self, query: str) -> RoutedQuery:
        entities = self.linker.link(query)
        intent, filters = route(query, entities)
        return RoutedQuery(raw=query, entities=entities,
                           intent=intent, filters=filters)
