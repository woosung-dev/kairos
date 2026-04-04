"use client";

import { TodayFeed } from "@/features/home/components/today-feed";

export default function HomePage() {
  // [가정] 실제 서비스에서는 백엔드 데이터 존재 여부로 isEmpty를 결정
  // Phase 1에서는 mock 데이터 기반으로 피드 표시
  return <TodayFeed />;
}
