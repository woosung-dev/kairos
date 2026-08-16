# 보안 취약점 신고

취약점은 **공개 Issue 로 열지 말아 주세요.**

- GitHub **Security → Report a vulnerability** (private vulnerability reporting)
- 또는 메인테이너에게 직접 연락

## 범위

- 프로덕션: `kairos.woosung.dev` · `kairos-api.woosung.dev`
- 이 저장소의 코드

## 우선 확인 대상

멀티테넌시 격리가 이 제품의 핵심 보안 경계입니다. 아래는 특히 중요하게 다룹니다.

- 워크스페이스 간 데이터 접근 (cross-tenant IDOR)
- 프로젝트 `visibility`(public / draft / private) 우회
- RBAC 우회 (owner / admin / member / viewer)
- RAG 응답에 접근 권한 없는 소스가 인용되는 경우

## 응답

1인 운영 프로젝트라 즉시 응답은 어렵습니다. 접수 확인은 영업일 기준 며칠 내에 드립니다.
