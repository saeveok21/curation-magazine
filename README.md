# curation-magazine

개인용 큐레이션 매거진의 수집기입니다.

- `sources.json` — 수집할 소스 목록 (여기에 추가/삭제)
- `scripts/collect.py` — 새 콘텐츠를 모아 `data/items.json`에 저장
- `.github/workflows/collect.yml` — 3시간마다 자동 실행 (Actions 탭에서 수동 실행 가능)
- `data/status.json` — 마지막 실행에서 소스별 성공/실패

요약과 페이지 반영은 Claude 예약 작업이 `data/items.json`을 읽어 처리합니다.
