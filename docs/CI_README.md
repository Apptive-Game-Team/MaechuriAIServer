# CI/CD 설정

이 저장소는 GitHub Actions를 사용하여 자동으로 Docker 이미지를 빌드하고 GitHub Container Registry (GHCR)에 푸시하는 CI(Continuous Integration)를 구성합니다.

## 개요

CI 워크플로우는 자동으로 다음을 수행합니다:
- ARM64 Linux 아키텍처용 FastAPI 애플리케이션의 Docker 이미지 빌드
- 이미지를 GitHub Container Registry (ghcr.io)에 푸시
- 브랜치 이름, 커밋 SHA, 기본 브랜치의 `latest` 태그로 이미지 태깅

## 필수 설정

### 1. GitHub Secrets 설정

CI 워크플로우를 실행하려면 GitHub 저장소에 두 개의 시크릿을 설정해야 합니다:

1. **GHCR_USER**: GitHub 사용자 이름
2. **GHCR_TOKEN**: `write:packages` 권한이 있는 GitHub Personal Access Token (PAT)

#### GitHub Personal Access Token 생성 방법:

1. GitHub 설정 → Developer settings → Personal access tokens → Tokens (classic)로 이동
2. "Generate new token (classic)" 클릭
3. 설명이 포함된 이름 입력 (예: "GHCR CI Token")
4. 다음 범위 선택:
   - `write:packages` (이미지 푸시용)
   - `read:packages` (이미지 풀용)
   - `delete:packages` (선택사항, 오래된 이미지 삭제용)
5. "Generate token" 클릭
6. 토큰 복사 (다시 볼 수 없습니다!)

#### 저장소에 시크릿 추가 방법:

1. GitHub에서 저장소로 이동
2. Settings → Secrets and variables → Actions 클릭
3. "New repository secret" 클릭
4. GitHub 사용자 이름으로 `GHCR_USER` 추가
5. 생성한 Personal Access Token으로 `GHCR_TOKEN` 추가

### 2. 워크플로우 트리거

CI 워크플로우는 다음 상황에서 자동으로 실행됩니다:
- `main` 브랜치에 코드가 푸시될 때

## Docker 이미지

Docker 이미지는 다음을 사용하여 빌드됩니다:
- **베이스 이미지**: `python:3.12-slim`
- **아키텍처**: `linux/arm64` (ARM Linux 서버용 ARM 64비트)
- **애플리케이션**: 포트 8000에서 실행되는 FastAPI 앱
- **명령어**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### 이미지 태그

이미지는 다음으로 태그됩니다:
- 브랜치 이름 (예: `ghcr.io/apptive-game-team/maechuri-ai:main`)
- 브랜치와 커밋 SHA (예: `ghcr.io/apptive-game-team/maechuri-ai:main-abc1234`)
- 기본 브랜치의 `latest` 태그

### 이미지 가져오기

워크플로우가 성공적으로 실행되면 이미지를 가져올 수 있습니다:

```bash
# GHCR 로그인
echo $GHCR_TOKEN | docker login ghcr.io -u $GHCR_USER --password-stdin

# 이미지 가져오기
docker pull ghcr.io/apptive-game-team/maechuri-ai:latest

# 컨테이너 실행
docker run -d -p 8000:8000 --env-file .env ghcr.io/apptive-game-team/maechuri-ai:latest
```

## 파일

- **Dockerfile**: Docker 이미지를 빌드하는 방법 정의
- **.dockerignore**: Docker 빌드 컨텍스트에서 제외할 파일 지정
- **.github/workflows/ci.yml**: GitHub Actions 워크플로우 설정

## 지속적 배포 (CD)

CI 워크플로우는 Docker 이미지를 빌드하고 푸시만 합니다. 배포를 위해 서버에서 최신 이미지를 가져올 수 있습니다:

```bash
docker pull ghcr.io/apptive-game-team/maechuri-ai:latest
docker-compose up -d
```

이는 이슈에서 언급된 풀 기반 배포 모델을 따릅니다.
