import random
from typing import Optional, List, Dict, Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from app.models.quiz import Quiz, QuizProblem, UserQuizAttempt
from app.models.user import User
from app.schemas.quiz import (
    QuizPagination, QuizListItem, QuizUserPagination, 
    QuizListItemForUser, Quiz as QuizSchema, 
    QuizProblemPage, QuizProblemForUser
)
import math


def get_quiz_list(
    db: Session, 
    page: int = 1, 
    size: int = 10, 
    active_only: bool = True, 
    current_user: Optional[User] = None
):
    """퀴즈 목록 조회 쿼리 처리"""
    # 기본 쿼리 - soft delete되지 않은 것만 가져옴
    query = db.query(
        Quiz,
        func.count(QuizProblem.id).label("problems_count")
    ).outerjoin(
        QuizProblem, Quiz.id == QuizProblem.quiz_id
    ).filter(
        Quiz.deleted_at == None
    )
    
    # 활성화 퀴즈 필터링
    if active_only:
        query = query.filter(Quiz.is_active == True)
    
    # 그룹화 및 정렬
    query = query.group_by(Quiz.id).order_by(Quiz.created_at.desc())
    
    # 전체 개수 계산
    total = query.count()
    
    # 페이지네이션 적용
    items = query.offset((page - 1) * size).limit(size).all()
    
    # 관리자와 일반 사용자 구분 처리
    if current_user and not current_user.is_superuser:
        # 일반 사용자인 경우 응시 정보 포함
        quiz_list = []
        
        # 일괄 조회를 통한 성능 향상
        quiz_ids = [q.id for q, _ in items]
        attempts_map = {}
        
        if quiz_ids:
            # 한 번의 쿼리로 해당 사용자의 모든 퀴즈 응시 정보 가져오기
            attempts = db.query(UserQuizAttempt).filter(
                UserQuizAttempt.quiz_id.in_(quiz_ids),
                UserQuizAttempt.user_id == current_user.id
            ).all()
            
            # 퀴즈 ID를 키로 하는 맵 생성
            attempts_map = {attempt.quiz_id: attempt for attempt in attempts}
        
        for q, problems_count in items:
            # 맵에서 해당 퀴즈의 응시 정보 조회
            attempt = attempts_map.get(q.id)
            
            is_attempted = False
            is_completed = False
            score = None
            
            if attempt:
                is_attempted = True
                is_completed = attempt.completed
                score = attempt.score
            
            quiz_list.append(
                QuizListItemForUser(
                    id=q.id,
                    title=q.title,
                    type=q.type,
                    is_active=q.is_active,
                    description=q.description,
                    problems_count=problems_count,
                    problems_per_page=q.problems_per_page,
                    total_problems=q.total_problems,
                    created_at=q.created_at,
                    is_attempted=is_attempted,
                    is_completed=is_completed,
                    score=score
                )
            )
        
        # 사용자용 페이지네이션 응답 생성
        return QuizUserPagination(
            total=total,
            items=quiz_list,
            page=page,
            size=size,
            pages=math.ceil(total / size)
        )
    else:
        # 관리자인 경우 기본 정보만 제공
        quiz_list = []
        for q, problems_count in items:
            quiz_list.append(
                QuizListItem(
                    id=q.id,
                    title=q.title,
                    type=q.type,
                    is_active=q.is_active,
                    description=q.description,
                    problems_count=problems_count,
                    problems_per_page=q.problems_per_page,
                    total_problems=q.total_problems,
                    created_at=q.created_at
                )
            )
        
        # 관리자용 페이지네이션 응답 생성
        return QuizPagination(
            total=total,
            items=quiz_list,
            page=page,
            size=size,
            pages=math.ceil(total / size)
        )


def get_quiz_detail(db: Session, quiz_id: int):
    """퀴즈 상세 조회 쿼리 처리 (관리자용)"""
    # 한 번의 쿼리로 퀴즈와 모든 문제 함께 가져오기
    quiz = db.query(Quiz).options(
        joinedload(Quiz.problems)
    ).filter(
        Quiz.id == quiz_id, 
        Quiz.deleted_at == None
    ).first()
    
    if not quiz:
        return None
    
    # Pydantic 모델로 변환하여 반환
    return QuizSchema.from_orm(quiz)


def get_quiz_problems_for_user(
    db: Session, 
    quiz_id: int, 
    page: int = 1, 
    user_id: Optional[int] = None
):
    """퀴즈 문제 페이지 조회 (사용자용)"""
    # 퀴즈 기본 정보 조회 - 필요한 필드만 선택적으로 조회
    quiz = db.query(
        Quiz.id, 
        Quiz.title, 
        Quiz.description, 
        Quiz.random_order, 
        Quiz.problems_per_page, 
        Quiz.total_problems, 
        Quiz.shuffle_options
    ).filter(
        Quiz.id == quiz_id, 
        Quiz.is_active == True,
        Quiz.deleted_at == None
    ).first()
    
    if not quiz:
        return None
    
    # 사용자 응시 기록 확인
    user_attempt = None
    if user_id:
        user_attempt = db.query(UserQuizAttempt).filter(
            UserQuizAttempt.quiz_id == quiz_id,
            UserQuizAttempt.user_id == user_id,
            UserQuizAttempt.completed == False  # 완료되지 않은 응시만 조회
        ).first()
    
    # 기존 응시 기록이 있는 경우 해당 문제 목록 사용
    if user_attempt and user_attempt.attempted_problems:
        problem_ids = user_attempt.attempted_problems
        
        # 필요한 필드만 선택적으로 조회하여 성능 향상
        problems = db.query(
            QuizProblem.id, 
            QuizProblem.content, 
            QuizProblem.choices, 
            QuizProblem.answer_index
        ).filter(
            QuizProblem.id.in_(problem_ids),
            QuizProblem.deleted_at == None
        ).all()
    else:
        # 퀴즈 문제 전체 목록 조회 - 필요한 필드만 선택
        all_problems = db.query(
            QuizProblem.id, 
            QuizProblem.content, 
            QuizProblem.choices, 
            QuizProblem.answer_index
        ).filter(
            QuizProblem.quiz_id == quiz_id,
            QuizProblem.deleted_at == None
        ).all()
        
        # 문제가 없는 경우
        if not all_problems:
            return None
        
        # 새로운 응시 시작
        # 문제 출제 수 결정
        problems_count = len(all_problems)
        if quiz.total_problems > 0 and quiz.total_problems < problems_count:
            problems_count = quiz.total_problems
            # 무작위 문제 선택
            problems = random.sample(all_problems, problems_count)
        else:
            # 전체 문제 출제
            problems = all_problems
        
        # 문제 ID 목록 저장
        problem_ids = [p.id for p in problems]
        
        # 사용자 응시 기록 저장
        if user_id:
            if user_attempt:
                # 기존 응시 기록 업데이트
                user_attempt.attempted_problems = problem_ids
                db.commit()
            else:
                # 새 응시 기록 생성
                new_attempt = UserQuizAttempt(
                    user_id=user_id,
                    quiz_id=quiz_id,
                    attempted_problems=problem_ids,
                    completed=False
                )
                db.add(new_attempt)
                db.commit()
                user_attempt = new_attempt
    
    # 무작위 배치가 설정된 경우 문제 순서 섞기
    ordered_problems = problems.copy()
    if quiz.random_order:
        random.shuffle(ordered_problems)
    
    # 페이지 정보 계산
    problems_per_page = quiz.problems_per_page
    total_pages = math.ceil(len(ordered_problems) / problems_per_page)
    
    # 페이지 범위 체크
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
    
    # 현재 페이지의 문제 추출
    start_idx = (page - 1) * problems_per_page
    end_idx = start_idx + problems_per_page
    page_problems = ordered_problems[start_idx:end_idx]
    
    # 임시 저장된 답안 가져오기
    temporary_answers = {}
    if user_attempt and user_attempt.temporary_answers:
        temporary_answers = user_attempt.temporary_answers
    
    # 문제별로 정보 변환 (답안 제외)
    problems_for_user = []
    for problem in page_problems:
        # 선택지 복사
        choices = problem.choices.copy()
        
        # 선택지 섞기 옵션이 활성화된 경우
        if quiz.shuffle_options:
            # 정답을 기억하기 위해 정답 인덱스와 값을 저장
            correct_answer = choices[problem.answer_index]
            
            # 선택지 섞기
            random.shuffle(choices)
            
            # 문제 자체는 변경하지 않음 (정답 인덱스는 DB에 저장된 상태 유지)
        
        # 임시 저장된 답안이 있으면 추가
        selected_index = None
        if str(problem.id) in temporary_answers:
            selected_index = temporary_answers[str(problem.id)]
        
        problems_for_user.append(
            QuizProblemForUser(
                id=problem.id,
                content=problem.content,
                choices=choices,
                selected_index=selected_index
            )
        )
    
    # 페이지 응답 생성
    return QuizProblemPage(
        quiz_id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        current_page=page,
        total_pages=total_pages,
        problems=problems_for_user
    )


def get_user_quiz_status(db: Session, quiz_id: int, user_id: int):
    """사용자의 퀴즈 응시 상태 조회"""
    # 퀴즈 정보 확인
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.is_active == True,
        Quiz.deleted_at == None
    ).first()
    
    if not quiz:
        return None
    
    # 사용자 응시 정보 조회
    attempt = db.query(UserQuizAttempt).filter(
        UserQuizAttempt.user_id == user_id,
        UserQuizAttempt.quiz_id == quiz_id
    ).first()
    
    if not attempt:
        return {
            "quiz_id": quiz_id,
            "title": quiz.title,
            "is_attempted": False,
            "is_completed": False
        }
    
    # 답안 정보 가져오기
    answers = {}
    if attempt.completed and attempt.answers:
        answers = attempt.answers
    elif not attempt.completed and attempt.temporary_answers:
        answers = attempt.temporary_answers
    
    # 풀이 진행 상황 계산
    progress = 0
    if attempt.attempted_problems:
        answered_count = len(answers.keys())
        total_count = len(attempt.attempted_problems)
        if total_count > 0:
            progress = round((answered_count / total_count) * 100)
    
    return {
        "quiz_id": quiz_id,
        "title": quiz.title,
        "is_attempted": True,
        "is_completed": attempt.completed,
        "score": attempt.score,
        "progress": progress,
        "current_answers": answers,
        "attempted_problems": attempt.attempted_problems,
        "created_at": attempt.created_at,
        "completed_at": attempt.completed_at
    } 