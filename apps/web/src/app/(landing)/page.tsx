import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { LandingPage } from "@/components/landing/landing-page";

export default async function RootPage() {
  const { userId } = await auth();

  // 로그인 상태면 대시보드(RAG 홈)로 리다이렉트
  if (userId) {
    redirect("/dashboard");
  }

  // 비인증: 랜딩 페이지 — (landing)/layout.tsx의 data-theme="landing" wrapper에서 테마 적용
  return <LandingPage />;
}
