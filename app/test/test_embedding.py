"""
Embedding Service 테스트
- SBERT 모델 로딩 테스트
- 임베딩 생성 테스트
- 유사도 계산 테스트
- 다국어 지원 테스트
"""

import json
import os
from datetime import datetime
from sentence_transformers import util
import torch

from app.services.embedding.sbert_model import SBERTModel


OUTPUT_DIR = "app/test/output"


def embed_to_tensor(model: SBERTModel, text: str) -> torch.Tensor:
    """Helper function to convert text to embedding tensor."""
    return torch.tensor(model.embed(text))


def save_result(data: dict, prefix: str) -> str:
    """결과를 JSON 파일로 저장"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Result saved to: {filepath}")
    return filepath


def test_model_loading():
    """SBERT 모델 로딩 테스트"""
    print("=" * 50)
    print("TEST: Model Loading")
    print("=" * 50)

    try:
        print("Loading SBERT model...")
        model = SBERTModel()
        print("✓ Model loaded successfully!")
        return model
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        return None


def test_embedding_generation(model=None):
    """임베딩 생성 테스트"""
    print("\n" + "=" * 50)
    print("TEST: Embedding Generation")
    print("=" * 50)

    if model is None:
        model = test_model_loading()
        if model is None:
            return None

    test_texts = [
        "안녕하세요",
        "Hello, World!",
        "이것은 테스트 문장입니다.",
        "This is a test sentence.",
    ]

    results = []
    try:
        for text in test_texts:
            print(f"\nGenerating embedding for: '{text}'")
            embedding = model.embed(text)
            embedding_dim = len(embedding)

            print(f"  - Embedding dimension: {embedding_dim}")
            print(f"  - First 5 values: {embedding[:5]}")

            results.append(
                {
                    "text": text,
                    "embedding_dim": embedding_dim,
                    "embedding_sample": embedding[:5],
                }
            )

        print("\n✓ All embeddings generated successfully!")
        return results
    except Exception as e:
        print(f"✗ Embedding generation failed: {e}")
        return None


def test_similarity_calculation(model=None):
    """유사도 계산 테스트"""
    print("\n" + "=" * 50)
    print("TEST: Similarity Calculation")
    print("=" * 50)

    if model is None:
        model = test_model_loading()
        if model is None:
            return None

    # 유사한 문장 쌍
    similar_pairs = [
        ("안녕하세요", "안녕"),
        ("Hello", "Hi"),
        ("좋은 아침입니다", "좋은 아침이에요"),
    ]

    # 다른 문장 쌍
    different_pairs = [
        ("안녕하세요", "배가 고파요"),
        ("Hello", "I am hungry"),
        ("날씨가 좋아요", "컴퓨터가 고장났어요"),
    ]

    results = []

    print("\n--- Similar Pairs ---")
    for text1, text2 in similar_pairs:
        embedding1 = embed_to_tensor(model, text1)
        embedding2 = embed_to_tensor(model, text2)
        similarity = util.cos_sim(embedding1, embedding2).item()

        print(f"'{text1}' <-> '{text2}': {similarity:.4f}")
        results.append(
            {"pair": [text1, text2], "type": "similar", "similarity": similarity}
        )

    print("\n--- Different Pairs ---")
    for text1, text2 in different_pairs:
        embedding1 = embed_to_tensor(model, text1)
        embedding2 = embed_to_tensor(model, text2)
        similarity = util.cos_sim(embedding1, embedding2).item()

        print(f"'{text1}' <-> '{text2}': {similarity:.4f}")
        results.append(
            {"pair": [text1, text2], "type": "different", "similarity": similarity}
        )

    print("\n✓ Similarity calculation completed!")
    return results


def test_multilingual_support(model=None):
    """다국어 지원 테스트"""
    print("\n" + "=" * 50)
    print("TEST: Multilingual Support")
    print("=" * 50)

    if model is None:
        model = test_model_loading()
        if model is None:
            return None

    # 같은 의미의 다국어 문장
    multilingual_sentences = {
        "korean": "안녕하세요, 저는 김철수입니다.",
        "english": "Hello, I am Kim Chulsoo.",
        "japanese": "こんにちは、私はキム・チョルスです。",
    }

    results = []

    print("\n--- Generating Embeddings ---")
    embeddings = {}
    for lang, text in multilingual_sentences.items():
        print(f"{lang}: '{text}'")
        embeddings[lang] = embed_to_tensor(model, text)

    print("\n--- Cross-lingual Similarities ---")
    languages = list(multilingual_sentences.keys())
    for i in range(len(languages)):
        for j in range(i + 1, len(languages)):
            lang1, lang2 = languages[i], languages[j]
            similarity = util.cos_sim(embeddings[lang1], embeddings[lang2]).item()

            print(f"{lang1} <-> {lang2}: {similarity:.4f}")
            results.append(
                {
                    "lang1": lang1,
                    "lang2": lang2,
                    "text1": multilingual_sentences[lang1],
                    "text2": multilingual_sentences[lang2],
                    "similarity": similarity,
                }
            )

    print("\n✓ Multilingual support test completed!")
    return results


def test_full_pipeline():
    """전체 임베딩 테스트 파이프라인"""
    print("\n" + "=" * 50)
    print("TEST: Full Embedding Test Pipeline")
    print("=" * 50)

    all_results = {}

    # 1. 모델 로딩
    model = test_model_loading()
    if model is None:
        print("Pipeline failed at model loading")
        return

    # 2. 임베딩 생성
    embedding_results = test_embedding_generation(model)
    if embedding_results:
        all_results["embedding_generation"] = embedding_results

    # 3. 유사도 계산
    similarity_results = test_similarity_calculation(model)
    if similarity_results:
        all_results["similarity_calculation"] = similarity_results

    # 4. 다국어 지원
    multilingual_results = test_multilingual_support(model)
    if multilingual_results:
        all_results["multilingual_support"] = multilingual_results

    # 결과 저장
    if all_results:
        save_result(all_results, "embedding_test")

    print("\n" + "=" * 50)
    print("Full pipeline completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Embedding Service Test")
    parser.add_argument(
        "--loading", action="store_true", help="Test model loading only"
    )
    parser.add_argument(
        "--embedding", action="store_true", help="Test embedding generation only"
    )
    parser.add_argument(
        "--similarity", action="store_true", help="Test similarity calculation only"
    )
    parser.add_argument(
        "--multilingual", action="store_true", help="Test multilingual support only"
    )
    parser.add_argument("--full", action="store_true", help="Test full pipeline")

    args = parser.parse_args()

    if args.loading:
        test_model_loading()
    elif args.embedding:
        test_embedding_generation()
    elif args.similarity:
        test_similarity_calculation()
    elif args.multilingual:
        test_multilingual_support()
    elif args.full:
        test_full_pipeline()
    else:
        # 기본: 전체 파이프라인 테스트
        test_full_pipeline()
