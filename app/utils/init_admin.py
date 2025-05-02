import logging
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.database import SessionLocal
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_admin(db: Session) -> None:
    """
    관리자 계정이 없을 경우 초기 관리자 계정을 생성합니다.
    """
    admin_exists = db.query(User).filter(User.is_superuser == True).first()
    
    if not admin_exists:
        admin_user = User(
            email="admin@hjhquiz.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True
        )
        db.add(admin_user)
        db.commit()
        print("관리자 계정이 생성되었습니다.")
        print("이메일: admin@hjhquiz.com")
        print("비밀번호: admin123")
    else:
        print("관리자 계정이 이미 존재합니다.")


def main() -> None:
    """
    스크립트 실행 함수
    """
    logger.info("관리자 계정 생성 시작...")
    db = SessionLocal()
    try:
        init_admin(db)
    finally:
        db.close()
    logger.info("관리자 계정 생성 완료!")


if __name__ == "__main__":
    main() 