from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi_cache.decorator import cache
from fastapi_cache.coder import JsonCoder

from app.api.deps import get_db, get_current_active_superuser, get_current_user
from app.cqrs.command import quiz_commands
from app.cqrs.query import quiz_queries
from app.models.user import User
from app.schemas.quiz import (
    Quiz, QuizCreate, QuizUpdate, QuizPagination, 
    QuizUserPagination, QuizProblemPage, UserQuizSubmit,
    SaveTemporaryAnswers
)

router = APIRouter()


# 관리자용 API
@router.post("/", response_model=Quiz, status_code=201)
def create_quiz(
    quiz_in: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    퀴즈 생성 API - Admin 전용
    각 문제는 내용, 선택지 목록, 정답 인덱스를 포함합니다.
    선택지는 문자열 배열 형태로 직접 포함됩니다.
    """
    quiz = quiz_commands.create_quiz(db, quiz_in)
    return quiz


@router.get("/", response_model=QuizPagination)
@cache(expire=300, coder=JsonCoder) # 5분 캐싱
def read_quizzes(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    퀴즈 목록 조회 API - 모든 사용자
    관리자는 모든 퀴즈를 볼 수 있고, 일반 사용자는 응시 정보가 함께 제공됩니다.
    """
    # 사용자별 응시 정보는 캐싱에서 제외하기 위해 캐시 키에 사용자 ID 포함
    quizzes = quiz_queries.get_quiz_list(
        db, page=page, size=size, active_only=active_only, current_user=current_user
    )
    return quizzes


@router.get("/admin/{quiz_id}", response_model=Quiz)
@cache(expire=300, coder=JsonCoder) # 5분 캐싱
def read_quiz_admin(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    퀴즈 상세 조회 API - Admin 전용
    
    퀴즈의 모든 문제와 선택지를 포함한 상세 정보를 조회합니다.
    """
    quiz = quiz_queries.get_quiz_detail(db, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    return quiz


@router.put("/{quiz_id}", response_model=Quiz)
def update_quiz(
    quiz_id: int,
    quiz_in: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    퀴즈 수정 API - Admin 전용
    퀴즈 제목, 설명, 문제 목록, 랜덤 설정 등을 수정할 수 있습니다.
    문제와 선택지 목록도 함께 수정 가능합니다.
    """
    quiz = quiz_commands.update_quiz(db, quiz_id, quiz_in)
    return quiz


@router.delete("/{quiz_id}")
def delete_quiz(
    quiz_id: int,
    hard_delete: bool = Query(False, description="완전히 삭제할지 여부"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    퀴즈 삭제 API - Admin 전용
    hard_delete=True로 설정하면 데이터베이스에서 완전히 삭제되며,
    hard_delete=False(기본값)이면 soft delete로 처리됩니다.
    """
    result = quiz_commands.delete_quiz(db, quiz_id, hard_delete)
    return result


# 사용자 전용 API
@router.get("/{quiz_id}/problems", response_model=QuizProblemPage)
def get_quiz_problems(
    quiz_id: int,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    퀴즈 문제 페이지 조회 API - 사용자용
    
    페이지별로 문제를 조회합니다. 관리자 설정에 따라 문제가 랜덤으로 선택되고,
    선택지 순서가 섞일 수 있습니다.
    """
    result = quiz_queries.get_quiz_problems_for_user(
        db, quiz_id, page, current_user.id
    )
    if not result:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    return result


@router.post("/{quiz_id}/problems", response_model=QuizProblemPage)
def get_next_quiz_problems(
    quiz_id: int,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    다음 퀴즈 문제 페이지 조회 API - 사용자용
    
    다음 페이지의 문제를 조회합니다. 관리자 설정에 따라 문제가 랜덤으로 선택되고,
    선택지 순서가 섞일 수 있습니다. 임시 저장된 사용자 답안이 있으면 함께 반환됩니다.
    """
    result = quiz_queries.get_quiz_problems_for_user(
        db, quiz_id, page, current_user.id
    )
    if not result:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    return result


@router.post("/save-answers", status_code=200)
def save_answers(
    answer_data: SaveTemporaryAnswers,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    퀴즈 답안 임시 저장 API - 사용자용
    
    사용자가 퀴즈를 풀면서 선택한 답안을 임시 저장합니다.
    새로고침 후에도 사용자의 선택이 유지됩니다.
    """
    result = quiz_commands.save_temporary_answers(
        db, current_user.id, answer_data
    )
    return result


@router.post("/save-answer", status_code=200)
def save_single_answer(
    quiz_id: int = Query(..., description="퀴즈 ID"),
    problem_id: int = Query(..., description="문제 ID"),
    selected_index: int = Query(..., description="선택한 답안 인덱스"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    단일 문제 답안 임시 저장 API - 사용자용
    
    사용자가 문제 하나의 답안을 선택할 때마다 자동으로 임시 저장합니다.
    새로고침 후에도 사용자의 선택이 유지됩니다.
    """
    result = quiz_commands.save_single_answer(
        db, current_user.id, quiz_id, problem_id, selected_index
    )
    return result


@router.get("/{quiz_id}/user-status", status_code=200)
@cache(expire=60, coder=JsonCoder, key_builder=lambda r, *args, **kwargs: f"status_{r.path_params['quiz_id']}_{kwargs['current_user'].id}")
def get_user_quiz_status(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    사용자 퀴즈 응시 상태 조회 API
    
    사용자의 현재 퀴즈 응시 상태(진행 중/완료)와 임시 저장된 답안, 진행 상황 등을 조회합니다.
    새로고침 후에도 현재 진행 상황을 파악할 수 있습니다.
    """
    result = quiz_queries.get_user_quiz_status(
        db, quiz_id, current_user.id
    )
    if not result:
        raise HTTPException(status_code=404, detail="퀴즈 응시 정보를 찾을 수 없습니다")
    return result


@router.post("/submit", status_code=200)
def submit_quiz(
    submit_data: UserQuizSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    퀴즈 제출 API - 사용자용
    
    사용자가 퀴즈 답안을 제출하고 채점 결과를 받습니다.
    임시 저장된 답안과 최종 제출된 답안을 병합하여 채점합니다.
    """
    result = quiz_commands.submit_quiz_answers(
        db, current_user.id, submit_data
    )
    return result 