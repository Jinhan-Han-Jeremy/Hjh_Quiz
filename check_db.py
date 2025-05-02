"""
데이터베이스 구조를 확인하는 간단한 스크립트
실행: docker-compose exec web python check_db.py
"""

from app.db.database import engine
from sqlalchemy import text

def check_database():
    print("데이터베이스 구조 확인 중...")
    
    try:
        with engine.connect() as conn:
            # 테이블 목록 조회
            tables_result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in tables_result]
            print(f"테이블 목록: {tables}")
            
            # user_quiz_attempts 테이블 컬럼 확인
            if 'user_quiz_attempts' in tables:
                columns_result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user_quiz_attempts'"))
                columns = [row[0] for row in columns_result]
                print(f"user_quiz_attempts 테이블 컬럼: {columns}")
                
                # temporary_answers 컬럼 확인
                if 'temporary_answers' in columns:
                    print("✅ temporary_answers 컬럼이 성공적으로 추가되었습니다!")
                else:
                    print("❌ temporary_answers 컬럼이 없습니다!")
            else:
                print("user_quiz_attempts 테이블이 존재하지 않습니다.")
    
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_database() 