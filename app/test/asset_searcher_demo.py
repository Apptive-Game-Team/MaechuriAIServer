"""AssetSearcher 데모 실행 스크립트."""
import asyncio
import sys

from app.services.asset.asset_searcher import AssetSearcher


async def _demo(query: str, top_k: int = 5) -> None:
    """데모 실행: 미인덱싱 Asset 임베딩 후 쿼리 검색."""
    from dotenv import load_dotenv

    load_dotenv()

    searcher = AssetSearcher()

    # 1) embedding이 비어있는 Asset들에 임베딩 생성 및 저장
    print("=" * 60)
    print("1단계: embedding 미생성 Asset 인덱싱")
    print("=" * 60)
    indexed = await searcher.index_unindexed()
    print(f"  → {indexed}개 Asset에 임베딩을 생성했습니다.\n")

    # 2) 쿼리 문자열로 유사 Asset 검색 후 결과 출력
    print("=" * 60)
    print(f"2단계: 검색 쿼리 → \"{query}\"")
    print("=" * 60)
    results = await searcher.search(query, top_k=top_k)

    if not results:
        print("  검색 결과가 없습니다.")
        return

    for rank, r in enumerate(results, start=1):
        stars = _score_to_stars(r.similarity)
        print(f"\n  [{rank}위]  유사도: {stars}  ({r.similarity:.4f})")
        print(f"  prompt  : {r.prompt or '(없음)'}")
        print(f"  raw_url : {r.raw_url or '(없음)'}")


def _score_to_stars(similarity: float, max_stars: int = 5) -> str:
    """코사인 유사도 값(0~1)을 별(★) 표시로 변환합니다."""
    similarity = max(0.0, min(similarity, 1.0))
    filled = min(round(similarity * max_stars), max_stars)
    return "★" * filled + "☆" * (max_stars - filled)


if __name__ == "__main__":
    # 사용법: python -m app.test.asset_searcher_demo "검색할 내용"
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    search_query = sys.argv[1] if len(sys.argv) > 1 else "밝은 햇살이 비치는 정원 배경"
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    asyncio.run(_demo(search_query, top_k=k))
