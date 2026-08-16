import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { LandingPage } from "@/components/landing/landing-page";

export default async function RootPage() {
  // ADR-031: 세션 조회는 DB 를 한 번 탄다. 랜딩은 비로그인 트래픽이 대부분이라
  // 쿠키가 없으면 Better Auth 가 DB 를 건드리지 않고 곧장 null 을 돌려준다.
  const session = await auth.api.getSession({ headers: await headers() });

  // 로그인 상태면 대시보드(RAG 홈)로 리다이렉트
  if (session) {
    redirect("/dashboard");
  }

  // 비인증: 랜딩 페이지 — (landing)/layout.tsx의 data-theme="landing" wrapper에서 테마 적용
  return <LandingPage />;
}
