from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)
R = TypeVar('R')


class Query(BaseModel, Generic[T]):
    """쿼리 기본 클래스"""
    params: T


class QueryHandler(ABC, Generic[T, R]):
    """쿼리 핸들러 기본 클래스"""
    
    @abstractmethod
    async def handle(self, query: Query[T]) -> R:
        """쿼리를 처리합니다."""
        pass 