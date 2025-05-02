from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from sqlalchemy.orm import Session
from fastapi import HTTPException

from pydantic import BaseModel
from app.models import Quiz, QuizQuestion, QuizChoice
from app.api.deps import get_db

T = TypeVar('T', bound=BaseModel)
R = TypeVar('R')


class Command(BaseModel, Generic[T]):
    """명령 기본 클래스"""
    data: T


class CommandHandler(ABC, Generic[T, R]):
    """명령 핸들러 기본 클래스"""
    
    @abstractmethod
    async def handle(self, command: Command[T]) -> R:
        """명령을 처리합니다."""
        pass 


class CreateQuizCommand(BaseModel):
    title: str
    type: str
    is_active: bool = True
    description: str = ""
    questions: list


class UpdateQuizCommand(BaseModel):
    quiz_id: int
    title: str = None
    description: str = None
    is_active: bool = None
    questions: list = None


class DeleteQuizCommand(BaseModel):
    quiz_id: int


class CreateQuizHandler(CommandHandler[CreateQuizCommand, Quiz]):
    async def handle(self, command: Command[CreateQuizCommand]) -> Quiz:
        db: Session = get_db()
        quiz_data = command.data
        quiz = Quiz(
            title=quiz_data.title,
            type=quiz_data.type,
            is_active=quiz_data.is_active,
            description=quiz_data.description
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)

        for question_data in quiz_data.questions:
            question = QuizQuestion(
                quiz_id=quiz.id,
                content=question_data['content'],
                answer_index=question_data['answer_index']
            )
            db.add(question)
            db.commit()
            db.refresh(question)

            for choice_data in question_data['choices']:
                choice = QuizChoice(
                    question_id=question.id,
                    content=choice_data
                )
                db.add(choice)
            db.commit()

        return quiz


class UpdateQuizHandler(CommandHandler[UpdateQuizCommand, Quiz]):
    async def handle(self, command: Command[UpdateQuizCommand]) -> Quiz:
        db: Session = get_db()
        quiz_data = command.data
        quiz = db.query(Quiz).filter(Quiz.id == quiz_data.quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")

        if quiz_data.title is not None:
            quiz.title = quiz_data.title
        if quiz_data.description is not None:
            quiz.description = quiz_data.description
        if quiz_data.is_active is not None:
            quiz.is_active = quiz_data.is_active
        db.commit()

        # 문제 및 선택지 업데이트 로직 추가 필요
        # ...

        return quiz


class DeleteQuizHandler(CommandHandler[DeleteQuizCommand, dict]):
    async def handle(self, command: Command[DeleteQuizCommand]) -> dict:
        db: Session = get_db()
        quiz_data = command.data
        quiz = db.query(Quiz).filter(Quiz.id == quiz_data.quiz_id).first()
        if not quiz:
            raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")

        db.delete(quiz)
        db.commit()
        return {"detail": "퀴즈가 삭제되었습니다."} 