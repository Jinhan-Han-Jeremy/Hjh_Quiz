from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    random_order = Column(Boolean, default=False)  # 문제 순서 랜덤 여부
    problems_per_page = Column(Integer, default=10)  # 한 페이지당 문제 수
    total_problems = Column(Integer, default=0)  # 총 출제 문항 수 (0=전체)
    shuffle_options = Column(Boolean, default=False)  # 선택지 순서 랜덤 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft delete용

    # 관계 설정 - 퀴즈(one) : 퀴즈 문제(many)
    problems = relationship("QuizProblem", back_populates="quiz", cascade="all, delete-orphan")
    # 관계 설정 - 퀴즈(one) : 퀴즈 응시 기록(many)
    user_attempts = relationship("UserQuizAttempt", back_populates="quiz")


class QuizProblem(Base):
    __tablename__ = "quiz_problems"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    content = Column(String, nullable=False)  # 문제 내용
    choices = Column(JSON, nullable=False)  # 선택지 목록 (JSON 배열 형태)
    answer_index = Column(Integer, nullable=False)  # 정답 인덱스
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft delete용

    # 관계 설정
    quiz = relationship("Quiz", back_populates="problems")


class UserQuizAttempt(Base):
    __tablename__ = "user_quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    completed = Column(Boolean, default=False)  # 완료 여부
    score = Column(Integer, nullable=True)  # 점수
    answers = Column(JSON, nullable=True)  # 사용자 응답 (JSON 배열 형태)
    temporary_answers = Column(JSON, nullable=True)  # 임시 저장된 사용자 응답 (JSON 객체 형태)
    attempted_problems = Column(JSON, nullable=True)  # 출제된 문제 ID 목록 (JSON 배열 형태)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 시작 시간
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 완료 시간

    # 관계 설정
    user = relationship("User", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="user_attempts")