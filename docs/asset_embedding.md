# Asset Embedding 기능 문서

## 개요

`asset` 테이블의 `prompt` 컬럼에 BGE-M3 임베딩을 추가하여, 프롬프트 기반의 의미론적(semantic) 검색이 가능하도록 구현한 기능에 대한 문서입니다.  
프로젝트 전반에서 사용하는 동일한 임베딩 모델(BGE-M3, 1024차원)을 재사용합니다.

---

## 변경된 DB 스키마

아래 SQL 마이그레이션이 적용되어 있어야 합니다.

```sql
ALTER TABLE asset RENAME COLUMN meta_file_url TO final_url;
ALTER TABLE asset ALTER COLUMN final_url DROP NOT NULL;
ALTER TABLE asset ADD COLUMN IF NOT EXISTS prompt TEXT;
ALTER TABLE asset ADD COLUMN IF NOT EXISTS raw_url VARCHAR(512);
ALTER TABLE asset ADD COLUMN IF NOT EXISTS resized_url VARCHAR(512);
ALTER TABLE asset ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'COMPLETED';
ALTER TABLE asset ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE asset ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

이에 더해, ORM 레벨에서 `embedding` 컬럼이 추가됩니다.

```sql
-- pgvector 확장이 활성화되어 있어야 합니다
ALTER TABLE asset ADD COLUMN IF NOT EXISTS embedding vector(1024);
```

---

## 추가된 파일 목록

| 파일 | 설명 |
|------|------|
| `app/db/models/asset.py` | Asset ORM 모델 (`embedding` 컬럼 포함) |
| `app/db/repositories/asset_repository.py` | Asset CRUD + 임베딩 검색 레포지토리 |
| `app/services/asset/asset_searcher.py` | 의미론적 검색 서비스 (`AssetSearcher`) |
| `app/services/asset/__init__.py` | 서비스 패키지 초기화 |

---

## 파일 상세 설명

### `app/db/models/asset.py` — Asset ORM 모델

```python
class Asset(Base):
    __tablename__ = "asset"

    id: int               # PK, autoincrement
    final_url: str|None   # 최종 URL (비동기 생성 시 NULL 가능)
    raw_url: str|None     # 원본 URL
    resized_url: str|None # 리사이즈된 URL
    prompt: str|None      # 이미지 생성에 사용된 프롬프트
    status: str           # 상태값 (기본값: 'COMPLETED')
    created_at: datetime  # 생성 시각
    updated_at: datetime  # 수정 시각
    embedding: vector     # BGE-M3 임베딩 (1024차원), prompt로부터 생성
```

### `app/db/repositories/asset_repository.py` — AssetRepository

주요 메서드:

| 메서드 | 설명 |
|--------|------|
| `get_by_id(asset_id)` | ID로 단일 Asset 조회 |
| `get_all()` | 전체 Asset 목록 조회 |
| `save(asset)` | 신규 생성 또는 업데이트 후 저장 |
| `search_by_embedding(query_embedding, top_k, status)` | pgvector 코사인 거리 기반 의미론적 검색 |
| `update_embedding(asset_id, embedding)` | 특정 Asset의 임베딩 갱신 |

### `app/services/asset/asset_searcher.py` — AssetSearcher

의미론적 검색을 위한 서비스 클래스입니다.  
BGE-M3 임베딩 모델을 사용하여 쿼리를 벡터로 변환하고, `AssetRepository`를 통해 유사도 검색을 수행합니다.

주요 메서드:

| 메서드 | 설명 |
|--------|------|
| `search(query, top_k, status)` | 자연어 쿼리로 유사 Asset 검색 |
| `index_asset(asset)` | Asset의 prompt로부터 임베딩 생성 및 저장 |

---

## 사용 예시

### Asset 인덱싱 (임베딩 생성 및 저장)

```python
from app.db.models.asset import Asset
from app.services.asset import AssetSearcher

searcher = AssetSearcher()

# 새 Asset 생성 후 임베딩 저장
asset = Asset(
    prompt="밝은 햇살이 비치는 고풍스러운 서재, 나무 책장과 양초",
    status="COMPLETED",
    final_url="https://example.com/image.png",
)
# (DB에 먼저 저장 필요)
await searcher.index_asset(asset)
```

### Asset 검색

```python
from app.services.asset import AssetSearcher

searcher = AssetSearcher()

# 의미론적으로 유사한 Asset 검색
results = await searcher.search(
    query="서재 배경 이미지",
    top_k=5,
    status="COMPLETED",  # 완료된 Asset만 검색 (None이면 전체)
)

for result in results:
    print(result.prompt)
    print(result.final_url)
    print(result.status)
```

### 데모 스크립트 실행

```bash
python -m app.test.asset_searcher_demo "고풍스러운 서재 배경" 5
```

---

## 임베딩 모델

- **모델**: `BAAI/bge-m3` (HuggingFace)
- **차원**: 1024
- **언어**: 다국어 지원 (한국어 포함)
- **최대 토큰**: 8192
- **싱글톤 패턴**: `get_embedding_model()` / `get_embedding_service()` 를 통해 공유 인스턴스 사용

기존 `EmbeddingService`에 `embed_asset_prompt(prompt)` 메서드가 추가되었습니다.

---

## 아키텍처 다이어그램

```
[AssetSearcher]
    │
    ├── embed_query(query)  ──→ [EmbeddingService]
    │                                  │
    │                            [BGEM3Model]
    │                          (BAAI/bge-m3, 1024d)
    │
    └── search_by_embedding() ──→ [AssetRepository]
                                        │
                                   [PostgreSQL + pgvector]
                                   (asset.embedding 컬럼)
```

---

## 주의사항

1. **pgvector 확장 필요**: PostgreSQL에 `pgvector` 확장이 활성화되어 있어야 합니다.
2. **DB 마이그레이션**: 위의 SQL 마이그레이션을 먼저 적용해야 합니다.
3. **임베딩 없는 Asset**: `embedding` 컬럼이 `NULL`인 Asset은 `search_by_embedding()` 결과에서 제외됩니다.
4. **비동기 환경**: `AssetRepository`와 `AssetSearcher`의 모든 DB 관련 메서드는 `async/await`를 사용합니다.
