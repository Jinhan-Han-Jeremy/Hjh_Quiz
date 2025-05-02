from app.db.database import Base, engine

def update_database():
    print("데이터베이스 스키마 업데이트 중...")
    
    # 스키마 업데이트
    Base.metadata.create_all(engine)
    
    print("데이터베이스 스키마 업데이트 완료!")

if __name__ == "__main__":
    update_database() 