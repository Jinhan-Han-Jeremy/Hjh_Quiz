import uvicorn
import os

if __name__ == "__main__":
    # 환경 변수가 설정되어 있지 않다면 기본값 사용
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "True").lower() in ("true", "1", "t")
    
    # 서버 실행
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    ) 