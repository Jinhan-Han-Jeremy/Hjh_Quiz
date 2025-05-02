"""
데이터베이스 스키마를 업데이트하기 위한 스크립트
실행 방법: 
- Docker 환경: docker-compose exec web python update_schema.py
- 로컬 환경: python update_schema.py
"""

import os
import sys
from sqlalchemy import inspect, text
from app.db.database import Base, engine, SessionLocal
from app.models.quiz import Quiz, QuizProblem, UserQuizAttempt
from app.models.user import User

def check_db_connection():
    """데이터베이스 연결 확인"""
    try:
        # 연결 테스트
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"데이터베이스 연결 오류: {e}")
        return False

def update_database():
    """데이터베이스 스키마 업데이트"""
    print("데이터베이스 스키마 업데이트 중...")
    
    # 데이터베이스 연결 확인
    if not check_db_connection():
        print("데이터베이스에 연결할 수 없습니다. 설정을 확인하세요.")
        sys.exit(1)
    
    # 테이블 존재 여부 확인
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"현재 데이터베이스 테이블: {tables}")
    
    # 스키마 업데이트
    Base.metadata.create_all(bind=engine)
    
    # user_quiz_attempts 테이블에 temporary_answers 컬럼 존재 여부 확인
    if "user_quiz_attempts" in tables:
        columns = [c["name"] for c in inspector.get_columns("user_quiz_attempts")]
        if "temporary_answers" not in columns:
            print("user_quiz_attempts 테이블에 temporary_answers 컬럼 추가 필요")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE user_quiz_attempts ADD COLUMN IF NOT EXISTS temporary_answers JSONB"))
                    conn.commit()
                print("temporary_answers 컬럼이 성공적으로 추가되었습니다.")
            except Exception as e:
                print(f"컬럼 추가 중 오류 발생: {e}")
        else:
            print("temporary_answers 컬럼이 이미 존재합니다.")
    
    print("데이터베이스 스키마 업데이트 완료!")

if __name__ == "__main__":
    update_database() 