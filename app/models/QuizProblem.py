from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base

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