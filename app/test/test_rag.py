"""
RAG (Retrieval-Augmented Generation) 전체 파이프라인 테스트

테스트 항목:
1. BGE-M3 모델 로딩
2. 임베딩 서비스 테스트
3. 시나리오 인덱싱 (DB에 임베딩 저장)
4. 벡터 검색 테스트 (타임라인, 비밀, 단서)
5. 대화 히스토리 인덱싱 및 검색
6. 컨텍스트 빌딩 테스트
7. 전체 RAG 서비스 통합 테스트

사용법:
    python -m app.test.test_rag --full          # 전체 테스트
    python -m app.test.test_rag --model         # 모델 로딩만
    python -m app.test.test_rag --index         # 인덱싱만
    python -m app.test.test_rag --search        # 검색만
    python -m app.test.test_rag --context       # 컨텍스트 빌딩만
"""

import asyncio
import json
import os
import uuid
import sys
from datetime import datetime

# Windows 환경에서 ProactorEventLoop 이슈 방지 (Event loop is closed 에러 해결)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 환경 설정
from dotenv import load_dotenv

load_dotenv()

from sentence_transformers import util
import torch

from app.core.config import settings


OUTPUT_DIR = "app/test/output"
SCENARIO_ID = 1  # seed.sql에 있는 시나리오


def print_header(title: str):
    """섹션 헤더 출력"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_subheader(title: str):
    """서브섹션 헤더 출력"""
    print(f"\n--- {title} ---")


def print_success(msg: str):
    """성공 메시지"""
    print(f"✓ {msg}")


def print_error(msg: str):
    """에러 메시지"""
    print(f"✗ {msg}")


def print_info(msg: str):
    """정보 메시지"""
    print(f"  → {msg}")


def save_result(data: dict, prefix: str) -> str:
    """결과를 JSON 파일로 저장"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n결과 저장됨: {filepath}")
    return filepath


# ============================================================ 
# Core Logic Functions (Renamed from test_... to check_...)
# ============================================================ 

def check_model_loading():
    """BGE-M3 모델 로딩 테스트 로직"""
    print_header("1. BGE-M3 모델 로딩 테스트")

    try:
        print("BGE-M3 모델 로딩 중... (첫 실행 시 다운로드 필요)")
        from app.services.embedding.bge_m3_model import get_embedding_model

        model = get_embedding_model()

        print_success("모델 로딩 완료!")
        print_info("모델 이름: BAAI/bge-m3")
        print_info(f"임베딩 차원: {model.dimension}")

        # 싱글톤 테스트
        model2 = get_embedding_model()
        if model is model2:
            print_success("싱글톤 패턴 정상 동작")
        else:
            print_error("싱글톤 패턴 실패")

        return model
    except Exception as e:
        print_error(f"모델 로딩 실패: {e}")
        import traceback

        traceback.print_exc()
        return None


def check_embedding_service(model=None):
    """임베딩 서비스 테스트 로직"""
    print_header("2. 임베딩 서비스 테스트")

    try:
        from app.services.embedding import get_embedding_service

        service = get_embedding_service()
        print_success("임베딩 서비스 초기화 완료")

        # 2.1 기본 텍스트 임베딩
        print_subheader("2.1 기본 텍스트 임베딩")
        test_text = "어젯밤 10시에 뭐 했어?"
        embedding = service.embed_text(test_text)
        print_info(f"입력: '{test_text}'")
        print_info(f"임베딩 차원: {len(embedding)}")
        print_info(f"임베딩 샘플 (처음 5개): {embedding[:5]}")

        # 2.2 용의자 프로필 임베딩
        print_subheader("2.2 용의자 프로필 임베딩")
        profile_embedding = service.embed_suspect_profile(
            name="최영진",
            role="지도교수",
            description="명망 있는 뇌과학 분야의 지도교수. 항상 깔끔한 정장 차림.",
            age=50,
            gender="남성",
        )
        print_info(f"프로필 임베딩 차원: {len(profile_embedding)}")

        # 2.3 타임라인 임베딩
        print_subheader("2.3 타임라인 임베딩")
        timeline_embedding = service.embed_timeline_entry(
            time_range="23:00-23:30",
            location="최교수 연구실",
            activity="논문 작업",
            suspect_name="최영진",
        )
        print_info(f"타임라인 임베딩 차원: {len(timeline_embedding)}")

        # 2.4 비밀 임베딩
        print_subheader("2.4 비밀 임베딩")
        secret_embedding = service.embed_secret(
            content="최근 박선우와 연구 방향 문제로 다툰 것은 사실입니다.",
            suspect_name="최영진",
        )
        print_info(f"비밀 임베딩 차원: {len(secret_embedding)}")

        # 2.5 단서 임베딩
        print_subheader("2.5 단서 임베딩")
        clue_embedding = service.embed_clue_description(
            name="암호화된 뇌과학 수식",
            description="박선우 연구실 화이트보드에 복잡한 뇌과학 수식이 적혀있다.",
            found_at="박선우 개인 연구실",
        )
        print_info(f"단서 임베딩 차원: {len(clue_embedding)}")

        # 2.6 유사도 테스트
        print_subheader("2.6 유사도 테스트")
        queries = [
            "어젯밤 10시에 뭐 했어?",
            "10시쯤 뭐하고 있었나요?",
            "연구실에서 논문 작업을 했다",
            "날씨가 좋네요",
        ]

        reference = "23:00에 최교수 연구실에서 논문 작업을 하고 있었습니다."
        ref_embedding = torch.tensor(service.embed_text(reference))

        print_info(f"기준 문장: '{reference}'")
        print()
        for query in queries:
            query_embedding = torch.tensor(service.embed_text(query))
            similarity = util.cos_sim(query_embedding, ref_embedding).item()
            print(f"  '{query}' → 유사도: {similarity:.4f}")

        print_success("임베딩 서비스 테스트 완료")
        return service

    except Exception as e:
        print_error(f"임베딩 서비스 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return None


async def check_indexing():
    """시나리오 데이터 인덱싱 테스트 로직"""
    print_header("3. 시나리오 인덱싱 테스트")

    try:
        from sqlalchemy import text
        from app.db.database import async_session_factory
        from app.services.rag import get_rag_indexer

        indexer = get_rag_indexer()
        print_success("RAG Indexer 초기화 완료")

        async with async_session_factory() as db:
            # 기존 임베딩 확인
            print_subheader("3.1 기존 임베딩 상태 확인")

            result = await db.execute(
                text(
                    """
                SELECT COUNT(*) as total,
                       COUNT(profile_embedding) as with_embedding
                FROM suspect WHERE scenario_id = :sid
            """
                ),
                {"sid": SCENARIO_ID},
            )
            row = result.fetchone()
            print_info(f"용의자: 총 {row.total}명, 임베딩 있음: {row.with_embedding}명")

            result = await db.execute(
                text(
                    """
                SELECT COUNT(*) as total,
                       COUNT(embedding) as with_embedding
                FROM suspect_timeline WHERE scenario_id = :sid
            """
                ),
                {"sid": SCENARIO_ID},
            )
            row = result.fetchone()
            print_info(
                f"타임라인: 총 {row.total}개, 임베딩 있음: {row.with_embedding}개"
            )

            result = await db.execute(
                text(
                    """
                SELECT COUNT(*) as total,
                       COUNT(embedding) as with_embedding
                FROM suspect_secret WHERE scenario_id = :sid
            """
                ),
                {"sid": SCENARIO_ID},
            )
            row = result.fetchone()
            print_info(f"비밀: 총 {row.total}개, 임베딩 있음: {row.with_embedding}개")

            result = await db.execute(
                text(
                    """
                SELECT COUNT(*) as total,
                       COUNT(description_embedding) as with_embedding
                FROM clue WHERE scenario_id = :sid
            """
                ),
                {"sid": SCENARIO_ID},
            )
            row = result.fetchone()
            print_info(f"단서: 총 {row.total}개, 임베딩 있음: {row.with_embedding}개")

            # 인덱싱 실행
            print_subheader("3.2 인덱싱 실행")
            print("시나리오 데이터 인덱싱 중...")

            stats = await indexer.index_scenario(db, SCENARIO_ID)

            print_success("인덱싱 완료!")
            print_info(f"인덱싱된 용의자: {stats['suspects']}명")
            print_info(f"인덱싱된 단서: {stats['clues']}개")

            # 인덱싱 후 확인
            print_subheader("3.3 인덱싱 후 상태 확인")

            result = await db.execute(
                text(
                    """
                SELECT s.name, s.role,
                       CASE WHEN s.profile_embedding IS NOT NULL THEN 'O' ELSE 'X' END as profile,
                       (SELECT COUNT(*) FROM suspect_timeline t
                        WHERE t.scenario_id = s.scenario_id AND t.suspect_id = s.suspect_id
                        AND t.embedding IS NOT NULL) as timeline_count,
                       (SELECT COUNT(*) FROM suspect_secret sec
                        WHERE sec.scenario_id = s.scenario_id AND sec.suspect_id = s.suspect_id
                        AND sec.embedding IS NOT NULL) as secret_count
                FROM suspect s
                WHERE s.scenario_id = :sid
            """
                ),
                {"sid": SCENARIO_ID},
            )

            print("\n용의자별 인덱싱 상태:")
            print(
                f"{ '이름':<10} {'역할':<15} {'프로필':<8} {'타임라인':<10} {'비밀':<8}"
            )
            print("-" * 55)
            for row in result:
                print(
                    f"{row.name:<10} {row.role:<15} {row.profile:<8} {row.timeline_count:<10} {row.secret_count:<8}"
                )

            result = await db.execute(
                text(
                    """
                SELECT name,
                       CASE WHEN description_embedding IS NOT NULL THEN 'O' ELSE 'X' END as desc_emb,
                       CASE WHEN logic_embedding IS NOT NULL THEN 'O' ELSE 'X' END as logic_emb
                FROM clue
                WHERE scenario_id = :sid
            """
                ),
                {"sid": SCENARIO_ID},
            )

            print("\n단서별 인덱싱 상태:")
            print(f"{ '단서명':<25} {'설명 임베딩':<12} {'로직 임베딩':<12}")
            print("-" * 50)
            for row in result:
                print(f"{row.name:<25} {row.desc_emb:<12} {row.logic_emb:<12}")

        print_success("시나리오 인덱싱 테스트 완료")
        return True

    except Exception as e:
        print_error(f"인덱싱 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


async def check_retrieval():
    """벡터 검색 테스트 로직"""
    print_header("4. 벡터 검색 테스트")

    try:
        from app.db.database import async_session_factory
        from app.services.rag import get_rag_retriever

        retriever = get_rag_retriever()
        print_success("RAG Retriever 초기화 완료")

        async with async_session_factory() as db:
            # 4.1 타임라인 검색
            print_subheader("4.1 타임라인 검색")
            test_queries = [
                ("어젯밤 10시에 뭐 했어?", 1),  # 최영진
                ("자정쯤에 어디 있었어?", 1),  # 최영진
                ("언제 퇴근했어?", 2),  # 이수진
            ]

            for query, suspect_id in test_queries:
                print(f"\n쿼리: '{query}' (용의자 ID: {suspect_id})")
                results = await retriever.search_timelines(
                    db=db,
                    scenario_id=SCENARIO_ID,
                    suspect_id=suspect_id,
                    query=query,
                    top_k=3,
                    threshold=0.3,
                )

                if results:
                    for r in results:
                        print(
                            f"  [{r.similarity:.3f}] {r.time_range} - {r.location}: {r.activity[:30]}..."
                        )
                else:
                    print("  (검색 결과 없음)")

            # 4.2 비밀 검색
            print_subheader("4.2 비밀 검색 (pressure 조건 포함)")
            secret_queries = [
                ("박선우와 사이가 안 좋았다며?", 1, 40),  # pressure 40
                ("연구 아이디어 도용 문제", 1, 70),  # pressure 70
                ("범행을 자백해", 1, 95),  # pressure 95
            ]

            for query, suspect_id, pressure in secret_queries:
                print(f"\n쿼리: '{query}' (pressure: {pressure})")
                results = await retriever.search_secrets(
                    db=db,
                    scenario_id=SCENARIO_ID,
                    suspect_id=suspect_id,
                    query=query,
                    current_pressure=pressure,
                    top_k=2,
                    threshold=0.3,
                )

                if results:
                    for r in results:
                        print(
                            f"  [{r.similarity:.3f}] (threshold {r.threshold}) {r.content[:50]}..."
                        )
                else:
                    print("  (검색 결과 없음 - pressure 부족 또는 유사도 낮음)")

            # 4.3 단서 검색
            print_subheader("4.3 단서 검색")
            clue_queries = [
                "화이트보드에 뭐가 적혀있어?",
                "CCTV 기록 확인해봐",
                "살해 흉기는 뭐야?",
            ]

            for query in clue_queries:
                print(f"\n쿼리: '{query}'")
                results = await retriever.search_clues(
                    db=db,
                    scenario_id=SCENARIO_ID,
                    query=query,
                    top_k=2,
                    threshold=0.3,
                    search_type="description",
                )

                if results:
                    for r in results:
                        herring = " [RED HERRING]" if r.is_red_herring else ""
                        print(f"  [{r.similarity:.3f}] {r.name}{herring}")
                        print(f"      발견: {r.found_at}")
                else:
                    print("  (검색 결과 없음)")

        print_success("벡터 검색 테스트 완료")
        return True

    except Exception as e:
        print_error(f"검색 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


async def check_chat_history_indexing():
    """대화 히스토리 인덱싱 및 검색 테스트 로직"""
    print_header("5. 대화 히스토리 인덱싱 및 검색 테스트")

    try:
        from app.db.database import async_session_factory
        from app.services.rag import get_rag_indexer, get_rag_retriever

        indexer = get_rag_indexer()
        retriever = get_rag_retriever()

        # 테스트용 대화 생성
        session_id = str(uuid.uuid4())
        test_messages = [
            {"role": "user", "content": "어젯밤 10시에 어디 있었어?"},
            {
                "role": "suspect",
                "content": "제 연구실에서 논문 작업을 하고 있었습니다.",
            },
            {"role": "user", "content": "증인이 있어?"},
            {"role": "suspect", "content": "아니요, 혼자였습니다."},
            {"role": "user", "content": "박선우랑 사이가 안 좋았다며?"},
            {"role": "suspect", "content": "학문적인 논쟁이 있었을 뿐입니다."},
            {"role": "user", "content": "CCTV는 왜 꺼져있었어?"},
            {"role": "suspect", "content": "저는 그것에 대해 아는 바가 없습니다."},
        ]

        async with async_session_factory() as db:
            # 5.1 대화 인덱싱
            print_subheader("5.1 대화 메시지 인덱싱")
            print(f"세션 ID: {session_id}")
            print(f"인덱싱할 메시지 수: {len(test_messages)}")

            for i, msg in enumerate(test_messages):
                await indexer.index_chat_message(
                    db=db,
                    scenario_id=SCENARIO_ID,
                    session_id=session_id,
                    message_index=i,
                    role=msg["role"],
                    content=msg["content"],
                    suspect_id=1,
                    context="최영진",
                )
                print(f"  [{i}] {msg['role']}: {msg['content'][:40]}...")

            await db.commit()
            print_success("대화 인덱싱 완료")

            # 5.2 대화 검색
            print_subheader("5.2 대화 히스토리 검색")
            search_queries = [
                "10시에 뭐했냐고 했었지",
                "알리바이 증인",
                "CCTV 관련해서 뭐라고 했더라",
            ]

            for query in search_queries:
                print(f"\n쿼리: '{query}'")
                results = await retriever.search_chat_history(
                    db=db,
                    scenario_id=SCENARIO_ID,
                    session_id=session_id,
                    query=query,
                    top_k=3,
                    threshold=0.3,
                )

                if results:
                    for r in results:
                        role_label = "탐정" if r.role == "user" else "용의자"
                        print(
                            f"  [{r.similarity:.3f}] {role_label}: {r.content[:50]}..."
                        )
                else:
                    print("  (검색 결과 없음)")

        print_success("대화 히스토리 테스트 완료")
        return True

    except Exception as e:
        print_error(f"대화 히스토리 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


async def check_context_building():
    """컨텍스트 빌딩 테스트 로직"""
    print_header("6. 컨텍스트 빌딩 테스트")

    try:
        from app.db.database import async_session_factory
        from app.services.rag import get_rag_retriever, get_context_builder

        retriever = get_rag_retriever()
        builder = get_context_builder()

        print_success("Context Builder 초기화 완료")

        async with async_session_factory() as db:
            # 검색 실행
            query = "자정에 뭐 했어?"
            suspect_id = 1
            pressure = 50

            print_subheader("6.1 검색 결과")
            print(f"쿼리: '{query}'")
            print(f"용의자 ID: {suspect_id}, Pressure: {pressure}")

            timelines = await retriever.search_timelines(
                db=db,
                scenario_id=SCENARIO_ID,
                suspect_id=suspect_id,
                query=query,
                top_k=3,
                threshold=0.3,
            )
            print(f"\n검색된 타임라인: {len(timelines)}개")

            secrets = await retriever.search_secrets(
                db=db,
                scenario_id=SCENARIO_ID,
                suspect_id=suspect_id,
                query=query,
                current_pressure=pressure,
                top_k=2,
                threshold=0.3,
            )
            print(f"검색된 비밀: {len(secrets)}개")

            # 컨텍스트 빌딩
            print_subheader("6.2 빌드된 컨텍스트")

            timeline_ctx = builder.build_timeline_context(timelines)
            if timeline_ctx:
                print("\n[타임라인 컨텍스트]")
                print(timeline_ctx)

            secret_ctx = builder.build_secret_context(secrets)
            if secret_ctx:
                print("\n[비밀 컨텍스트]")
                print(secret_ctx)

            # 전체 컨텍스트
            print_subheader("6.3 통합 컨텍스트")
            full_ctx = builder.build_suspect_interrogation_context(
                timelines=timelines, secrets=secrets, chat_history=[]
            )
            if full_ctx:
                print(full_ctx)
            else:
                print("(컨텍스트 없음)")

        print_success("컨텍스트 빌딩 테스트 완료")
        return True

    except Exception as e:
        print_error(f"컨텍스트 빌딩 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


async def check_rag_service_integration():
    """전체 RAG 서비스 통합 테스트 로직"""
    print_header("7. RAG 서비스 통합 테스트")

    try:
        from app.db.database import async_session_factory
        from app.services.rag import get_rag_service

        rag_service = get_rag_service()
        print_success("RAG Service 초기화 완료")

        async with async_session_factory() as db:
            # 7.1 용의자 컨텍스트 검색
            print_subheader("7.1 용의자 심문 컨텍스트 검색")

            test_cases = [
                {"query": "10시에 뭐 했어?", "suspect_id": 1, "pressure": 30},
                {"query": "박선우와 왜 싸웠어?", "suspect_id": 1, "pressure": 60},
                {"query": "진실을 말해", "suspect_id": 1, "pressure": 90},
            ]

            for case in test_cases:
                print(f"\n[쿼리] '{case['query']}' (pressure: {case['pressure']})")

                context = await rag_service.get_suspect_context(
                    db=db,
                    scenario_id=SCENARIO_ID,
                    suspect_id=case["suspect_id"],
                    query=case["query"],
                    current_pressure=case["pressure"],
                    top_k_timeline=2,
                    top_k_secrets=2,
                    top_k_history=3,
                    similarity_threshold=0.3,
                )

                if context.full_context:
                    print("\n[검색된 컨텍스트]")
                    # 컨텍스트가 길면 일부만 출력
                    ctx_preview = context.full_context[:500]
                    if len(context.full_context) > 500:
                        ctx_preview += "..."
                    print(ctx_preview)
                else:
                    print("  (관련 컨텍스트 없음)")

            # 7.2 단서 분석 컨텍스트 검색
            print_subheader("7.2 단서 분석 컨텍스트 검색")

            clue_query = "이 수식이 뭘 의미하는 거야?"
            print(f"\n[쿼리] '{clue_query}'")

            clue_context = await rag_service.get_clue_context(
                db=db,
                scenario_id=SCENARIO_ID,
                clue_id=1,  # 암호화된 뇌과학 수식
                query=clue_query,
                top_k_clues=2,
                top_k_history=3,
                similarity_threshold=0.3,
            )

            if clue_context.full_context:
                print("\n[검색된 컨텍스트]")
                print(clue_context.full_context[:500])
            else:
                print("  (관련 컨텍스트 없음)")

        print_success("RAG 서비스 통합 테스트 완료")
        return True

    except Exception as e:
        print_error(f"RAG 서비스 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


# ============================================================ 
# Pytest Wrappers (test_... calling check_...)
# ============================================================ 

def test_model_loading():
    assert check_model_loading() is not None

def test_embedding_service():
    model = check_model_loading()
    assert check_embedding_service(model) is not None

async def test_indexing():
    assert await check_indexing() is True

async def test_retrieval():
    assert await check_retrieval() is True

async def test_chat_history_indexing():
    assert await check_chat_history_indexing() is True

async def test_context_building():
    assert await check_context_building() is True

async def test_rag_service_integration():
    assert await check_rag_service_integration() is True


# ============================================================ 
# 전체 테스트 파이프라인
# ============================================================ 
async def test_full_pipeline():
    """전체 RAG 테스트 파이프라인"""
    print_header("RAG 전체 테스트 파이프라인 시작")
    print(f"시나리오 ID: {SCENARIO_ID}")
    print(f"DB: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

    results = {
        "timestamp": datetime.now().isoformat(),
        "scenario_id": SCENARIO_ID,
        "tests": {},
    }

    # 1. 모델 로딩
    model = check_model_loading()
    results["tests"]["model_loading"] = model is not None

    if model is None:
        print_error("모델 로딩 실패로 테스트 중단")
        return

    # 2. 임베딩 서비스
    service = check_embedding_service(model)
    results["tests"]["embedding_service"] = service is not None

    # 3. 인덱싱
    indexing_ok = await check_indexing()
    results["tests"]["indexing"] = indexing_ok

    if not indexing_ok:
        print_error("인덱싱 실패로 검색 테스트 건너뜀")
    else:
        # 4. 검색
        retrieval_ok = await check_retrieval()
        results["tests"]["retrieval"] = retrieval_ok

        # 5. 대화 히스토리
        history_ok = await check_chat_history_indexing()
        results["tests"]["chat_history"] = history_ok

        # 6. 컨텍스트 빌딩
        context_ok = await check_context_building()
        results["tests"]["context_building"] = context_ok

        # 7. 통합 테스트
        integration_ok = await check_rag_service_integration()
        results["tests"]["integration"] = integration_ok

    # 결과 요약
    print_header("테스트 결과 요약")
    all_passed = True
    for test_name, passed in results["tests"].items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print_success("\n모든 테스트 통과!")
    else:
        print_error("\n일부 테스트 실패")

    # 결과 저장
    save_result(results, "rag_test")


# ============================================================ 
# 메인
# ============================================================ 
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 테스트")
    parser.add_argument("--model", action="store_true", help="모델 로딩만 테스트")
    parser.add_argument(
        "--embedding", action="store_true", help="임베딩 서비스만 테스트"
    )
    parser.add_argument("--index", action="store_true", help="인덱싱만 테스트")
    parser.add_argument("--search", action="store_true", help="검색만 테스트")
    parser.add_argument("--history", action="store_true", help="대화 히스토리만 테스트")
    parser.add_argument("--context", action="store_true", help="컨텍스트 빌딩만 테스트")
    parser.add_argument("--integration", action="store_true", help="통합 테스트만")
    parser.add_argument("--full", action="store_true", help="전체 테스트")

    args = parser.parse_args()

    if args.model:
        check_model_loading()
    elif args.embedding:
        m = check_model_loading()
        check_embedding_service(m)
    elif args.index:
        asyncio.run(check_indexing())
    elif args.search:
        asyncio.run(check_retrieval())
    elif args.history:
        asyncio.run(check_chat_history_indexing())
    elif args.context:
        asyncio.run(check_context_building())
    elif args.integration:
        asyncio.run(check_rag_service_integration())
    elif args.full:
        asyncio.run(test_full_pipeline())
    else:
        # 기본: 전체 테스트
        asyncio.run(test_full_pipeline())