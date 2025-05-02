from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# 기본 스키마
class QuizProblemBase(BaseModel):
    content: str
    choices: List[str] = Field(..., min_items=2, description="문제 선택지 목록")
    answer_index: int = Field(..., description="정답 선택지의 인덱스")


class QuizProblemCreate(QuizProblemBase):
    pass


class QuizBase(BaseModel):
    title: str
    type: str
    is_active: bool = True
    description: Optional[str] = None
    random_order: bool = False
    problems_per_page: int = 10
    total_problems: int = 0  # 0 = 전체 문제 출제
    shuffle_options: bool = False


class QuizCreate(QuizBase):
    problems: List[QuizProblemCreate] = Field(..., min_items=1, description="퀴즈 문제 목록")


# 수정용 스키마
class QuizProblemUpdate(QuizProblemBase):
    id: Optional[int] = None
    content: Optional[str] = None
    choices: Optional[List[str]] = None
    answer_index: Optional[int] = None
    delete: bool = False  # True이면 문제 삭제


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    random_order: Optional[bool] = None
    problems_per_page: Optional[int] = None
    total_problems: Optional[int] = None
    shuffle_options: Optional[bool] = None
    problems: Optional[List[QuizProblemUpdate]] = None


# 응답용 스키마
class QuizProblem(QuizProblemBase):
    id: int
    quiz_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Quiz(QuizBase):
    id: int
    problems: List[QuizProblem] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# 퀴즈 목록 조회 응답 - 관리자용
class QuizListItem(BaseModel):
    id: int
    title: str
    type: str
    is_active: bool
    description: Optional[str]
    problems_count: int
    problems_per_page: int
    total_problems: int
    created_at: datetime

    class Config:
        orm_mode = True


# 퀴즈 목록 조회 응답 - 사용자용
class QuizListItemForUser(QuizListItem):
    is_attempted: bool = False  # 응시 여부
    is_completed: bool = False  # 완료 여부
    score: Optional[int] = None  # 완료한 경우 점수
    
    class Config:
        orm_mode = True


class QuizPagination(BaseModel):
    total: int
    items: List[QuizListItem]
    page: int
    size: int
    pages: int


class QuizUserPagination(BaseModel):
    total: int
    items: List[QuizListItemForUser]
    page: int
    size: int
    pages: int


# 퀴즈 문제 페이지 응답
class QuizProblemForUser(BaseModel):
    id: int
    content: str
    choices: List[str]
    selected_index: Optional[int] = None  # 사용자가 선택한 답안 인덱스

    class Config:
        orm_mode = True


class QuizProblemPage(BaseModel):
    quiz_id: int
    title: str
    description: Optional[str] = None
    current_page: int
    total_pages: int
    problems: List[QuizProblemForUser]

    class Config:
        orm_mode = True


# 사용자 응답 스키마
class UserAnswer(BaseModel):
    problem_id: int
    selected_index: int


class UserQuizSubmit(BaseModel):
    quiz_id: int
    answers: List[UserAnswer]


# 임시 저장 스키마
class TemporaryAnswer(BaseModel):
    problem_id: int
    selected_index: int


class SaveTemporaryAnswers(BaseModel):
    quiz_id: int
    answers: List[TemporaryAnswer] 