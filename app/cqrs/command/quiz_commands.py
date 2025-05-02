from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.quiz import Quiz, QuizProblem, UserQuizAttempt
from app.schemas.quiz import QuizCreate, QuizUpdate, UserQuizSubmit, SaveTemporaryAnswers


def create_quiz(db: Session, quiz_data: QuizCreate):
    """퀴즈 생성 명령 처리"""
    # 퀴즈 생성
    quiz = Quiz(
        title=quiz_data.title,
        type=quiz_data.type,
        is_active=quiz_data.is_active,
        description=quiz_data.description,
        random_order=quiz_data.random_order,
        problems_per_page=quiz_data.problems_per_page,
        total_problems=quiz_data.total_problems,
        shuffle_options=quiz_data.shuffle_options
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    # 문제와 선택지 일괄 추가 (bulk insert)
    for problem_data in quiz_data.problems:
        # 문제와 선택지 함께 추가
        problem = QuizProblem(
            quiz_id=quiz.id,
            content=problem_data.content,
            choices=problem_data.choices,
            answer_index=problem_data.answer_index
        )
        db.add(problem)
    
    db.commit()
    return quiz


def update_quiz(db: Session, quiz_id: int, quiz_data: QuizUpdate):
    """퀴즈 수정 명령 처리"""
    # 퀴즈 조회
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    
    # 퀴즈 기본 정보 업데이트
    if quiz_data.title is not None:
        quiz.title = quiz_data.title
    if quiz_data.type is not None:
        quiz.type = quiz_data.type
    if quiz_data.description is not None:
        quiz.description = quiz_data.description
    if quiz_data.is_active is not None:
        quiz.is_active = quiz_data.is_active
    if quiz_data.random_order is not None:
        quiz.random_order = quiz_data.random_order
    if quiz_data.problems_per_page is not None:
        quiz.problems_per_page = quiz_data.problems_per_page
    if quiz_data.total_problems is not None:
        quiz.total_problems = quiz_data.total_problems
    if quiz_data.shuffle_options is not None:
        quiz.shuffle_options = quiz_data.shuffle_options
    
    db.commit()
    
    # 문제 업데이트
    if quiz_data.problems:
        existing_problem_ids = {p.id for p in quiz.problems}
        processed_problem_ids = set()
        
        for p_data in quiz_data.problems:
            if p_data.id:  # 기존 문제 수정
                problem = db.query(QuizProblem).filter(QuizProblem.id == p_data.id).first()
                if not problem:
                    continue
                
                if p_data.delete:  # 문제 삭제
                    db.delete(problem)
                else:  # 문제 수정
                    if p_data.content is not None:
                        problem.content = p_data.content
                    if p_data.choices is not None:
                        problem.choices = p_data.choices
                    if p_data.answer_index is not None:
                        problem.answer_index = p_data.answer_index
                    processed_problem_ids.add(problem.id)
            else:  # 새 문제 추가
                problem = QuizProblem(
                    quiz_id=quiz.id,
                    content=p_data.content if p_data.content is not None else "",
                    choices=p_data.choices if p_data.choices is not None else [],
                    answer_index=p_data.answer_index if p_data.answer_index is not None else 0
                )
                db.add(problem)
        
        # 처리되지 않은 문제 삭제
        for problem_id in existing_problem_ids - processed_problem_ids:
            problem = db.query(QuizProblem).filter(QuizProblem.id == problem_id).first()
            if problem:
                db.delete(problem)
        
        db.commit()
    
    return quiz


def delete_quiz(db: Session, quiz_id: int, hard_delete: bool = False):
    """퀴즈 삭제 명령 처리"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    
    if hard_delete:
        # Hard delete - DB에서 완전히 삭제
        db.delete(quiz)
        message = "퀴즈가 완전히 삭제되었습니다"
    else:
        # Soft delete - deleted_at 필드 업데이트
        quiz.deleted_at = datetime.now()
        quiz.is_active = False
        message = "퀴즈가 비활성화되었습니다"
    
    db.commit()
    return {"detail": message}


def save_temporary_answers(db: Session, user_id: int, data: SaveTemporaryAnswers):
    """사용자 퀴즈 답안 임시 저장"""
    # 퀴즈 확인
    quiz = db.query(Quiz).filter(
        Quiz.id == data.quiz_id,
        Quiz.is_active == True,
        Quiz.deleted_at == None
    ).first()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    
    # 기존 응시 기록 확인
    attempt = db.query(UserQuizAttempt).filter(
        UserQuizAttempt.user_id == user_id,
        UserQuizAttempt.quiz_id == data.quiz_id,
        UserQuizAttempt.completed == False
    ).first()
    
    if not attempt:
        raise HTTPException(status_code=400, detail="퀴즈 응시 기록이 없습니다")
    
    # 임시 답안 저장
    temp_answers = {answer.problem_id: answer.selected_index for answer in data.answers}
    attempt.temporary_answers = temp_answers
    
    db.commit()
    
    return {"detail": "답안이 임시 저장되었습니다"}


def submit_quiz_answers(db: Session, user_id: int, submit_data: UserQuizSubmit):
    """사용자 퀴즈 제출 처리"""
    # 퀴즈 확인 - 필요한 필드만 선택적으로 조회
    quiz = db.query(
        Quiz.id, 
        Quiz.title
    ).filter(
        Quiz.id == submit_data.quiz_id,
        Quiz.is_active == True,
        Quiz.deleted_at == None
    ).first()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    
    # 기존 응시 기록 확인
    attempt = db.query(UserQuizAttempt).filter(
        UserQuizAttempt.user_id == user_id,
        UserQuizAttempt.quiz_id == submit_data.quiz_id,
        UserQuizAttempt.completed == False
    ).first()
    
    if not attempt:
        raise HTTPException(status_code=400, detail="퀴즈 응시 기록이 없습니다")
    
    # 문제별 정답 확인 및 점수 계산
    total_questions = len(attempt.attempted_problems)
    if total_questions == 0:
        raise HTTPException(status_code=400, detail="응시한 문제가 없습니다")
    
    # 답안 저장
    submitted_answers = {str(answer.problem_id): answer.selected_index for answer in submit_data.answers}
    
    # 임시 저장된 답안과 병합 (제출된 답안이 우선)
    final_answers = {}
    if attempt.temporary_answers:
        final_answers.update(attempt.temporary_answers)
    final_answers.update(submitted_answers)
    
    # 최종 답안을 응시 기록에 저장
    attempt.answers = final_answers
    
    # 정답 확인 - 필요한 필드만 선택적으로 조회
    problem_ids = attempt.attempted_problems
    problems = db.query(
        QuizProblem.id, 
        QuizProblem.answer_index
    ).filter(
        QuizProblem.id.in_(problem_ids)
    ).all()
    
    problem_dict = {str(p.id): p.answer_index for p in problems}
    
    # 채점 (효율적인 방식으로 수정)
    correct_count = 0
    for problem_id in attempt.attempted_problems:
        str_problem_id = str(problem_id)
        if str_problem_id in final_answers and str_problem_id in problem_dict:
            if final_answers[str_problem_id] == problem_dict[str_problem_id]:
                correct_count += 1
    
    # 점수 계산 (100점 만점)
    score = round((correct_count / total_questions) * 100)
    
    # 응시 완료 처리
    now = datetime.now()
    attempt.score = score
    attempt.completed = True
    attempt.completed_at = now
    
    db.commit()
    
    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "total_questions": total_questions,
        "correct_count": correct_count,
        "score": score,
        "completed_at": now
    }


def save_single_answer(db: Session, user_id: int, quiz_id: int, problem_id: int, selected_index: int):
    """단일 문제 답안 임시 저장"""
    # 퀴즈 확인 - 필요한 필드만 선택적으로 조회
    quiz_exists = db.query(Quiz.id).filter(
        Quiz.id == quiz_id,
        Quiz.is_active == True,
        Quiz.deleted_at == None
    ).first() is not None
    
    if not quiz_exists:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
    
    # 기존 응시 기록 확인
    attempt = db.query(UserQuizAttempt).filter(
        UserQuizAttempt.user_id == user_id,
        UserQuizAttempt.quiz_id == quiz_id,
        UserQuizAttempt.completed == False
    ).first()
    
    if not attempt:
        raise HTTPException(status_code=400, detail="퀴즈 응시 기록이 없습니다")
    
    # 기존 임시 답안에 현재 선택을 추가 또는 업데이트
    temporary_answers = attempt.temporary_answers or {}
    temporary_answers[str(problem_id)] = selected_index
    attempt.temporary_answers = temporary_answers
    
    db.commit()
    
    return {"detail": "답안이 저장되었습니다"} 