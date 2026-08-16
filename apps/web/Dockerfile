# Kairos Frontend — OCI 셀프호스팅용 이미지 (ADR-028)
#
# 왜 멀티스테이지(컨테이너 내부 빌드)인가:
#   `next/image` 를 쓰므로 런타임에 sharp 네이티브 바이너리가 필요하다. 맥에서 `pnpm build` 한
#   .next/standalone 을 그대로 얹으면 darwin-arm64 바이너리가 들어가 리눅스에서 깨진다.
#   빌드를 컨테이너 안에서 하면 linuxmusl-arm64 바이너리가 설치된다.
#   맥(darwin/arm64) ↔ 서버(aarch64) 가 같은 아키텍처라 --platform linux/arm64 는 에뮬레이션 없이 돈다.

FROM node:22-alpine AS base
# lockfileVersion 6.0 = pnpm 8 계열. 로컬(8.15.9)과 문자 그대로 동일하게 고정해 재현성을 보장한다.
RUN corepack enable && corepack prepare pnpm@8.15.9 --activate

# ── deps: 의존성만 설치 (레이어 캐시) ──────────────────────────────────────
FROM base AS deps
# sharp 등 네이티브 모듈이 glibc 심볼을 찾는 경우 대비
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ── builder: next build ────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* 는 빌드타임에 번들로 인라인된다 (src/lib/api-client.ts:2).
# → 도메인이 바뀌면 반드시 재빌드해야 한다. 런타임 env 로는 바뀌지 않는다.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_RECALL_ENABLED
ARG NEXT_PUBLIC_FOUNDER_USER_ID
ARG NEXT_PUBLIC_APP_ENV
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_RECALL_ENABLED=$NEXT_PUBLIC_RECALL_ENABLED \
    NEXT_PUBLIC_FOUNDER_USER_ID=$NEXT_PUBLIC_FOUNDER_USER_ID \
    NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV \
    NEXT_TELEMETRY_DISABLED=1

# ADR-031: Better Auth 는 빌드타임 공개키 개념이 없다 — 인증 build-arg 가 0개다.
# 다만 `next build` 의 page data 수집이 auth.ts 를 평가하므로, 기본 secret 경고를
# 없애기 위해 빌드 전용 더미가 필요하다. 런타임 값은 compose 의 environment 가 준다.
#
# ★`ENV` 가 아니라 `RUN` 인라인으로 준다. ENV 로 두면 이미지 메타데이터에 남고
#   docker 가 SecretsUsedInArgOrEnv 로 경고한다 — 더미라도 그 경고가 매 빌드 노이즈가 되고,
#   진짜 시크릿이 섞여 들어갈 때 경고가 이미 무시되는 상태를 만든다.
RUN BETTER_AUTH_SECRET=build-time-placeholder-not-used-at-runtime pnpm build

# ── runner: standalone 산출물만 ────────────────────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
# HOSTNAME=0.0.0.0 이 없으면 standalone server.js 가 컨테이너 루프백에만 바인드해
# publish 포트로 들어갈 수 없다 (포트 매핑이 죽은 것처럼 보인다).

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# standalone 은 public / .next/static 을 스스로 담지 않는다 — 수동 복사해야 정적 자산이 서빙된다.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
