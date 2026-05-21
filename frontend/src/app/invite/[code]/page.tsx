"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useAuth, SignInButton } from "@clerk/nextjs";
import { Users, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useInviteInfo, useAcceptInvite } from "@/features/members/hooks";
import { useWorkspaceStore } from "@/features/workspaces/store";

export default function InvitePage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = use(params);
  const router = useRouter();
  const { isSignedIn } = useAuth();
  const { data: info, isLoading } = useInviteInfo(code);
  const acceptInvite = useAcceptInvite();
  const setActiveWorkspaceId = useWorkspaceStore((s) => s.setActiveWorkspaceId);

  const handleAccept = () => {
    acceptInvite.mutate(code, {
      onSuccess: (result) => {
        setActiveWorkspaceId(result.workspaceId);
        router.push("/");
      },
    });
  };

  // 로딩 상태
  // F-2C v2 (Sprint 25 polish, agy 발견): skip-link 타깃 누락. 외각 div → main.
  if (isLoading) {
    return (
      <main
        id="main-content"
        className="min-h-dvh flex items-center justify-center"
        style={{ background: "var(--background)" }}
      >
        <Loader2
          className="w-6 h-6 animate-spin"
          style={{ color: "var(--text-muted)" }}
        />
      </main>
    );
  }

  return (
    <main
      id="main-content"
      className="min-h-dvh flex items-center justify-center px-4"
      style={{ background: "var(--background)" }}
    >
      <Card className="w-full max-w-sm" style={{ background: "var(--surface)" }}>
        <CardContent className="pt-8 pb-6 px-6 text-center space-y-5">
          {/* 아이콘 */}
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto"
            style={{ background: "var(--surface-active)" }}
          >
            <Users className="w-7 h-7" style={{ color: "var(--accent)" }} />
          </div>

          {/* 워크스페이스 정보 */}
          {info?.isValid ? (
            <>
              <div className="space-y-1.5">
                <h1
                  className="text-lg font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  {info.workspaceName}
                </h1>
                {info.inviterName && (
                  <p
                    className="text-sm"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {info.inviterName}님이 초대했습니다
                  </p>
                )}
              </div>

              {/* 역할 뱃지 */}
              <Badge variant="secondary" className="text-xs">
                {info.role} 역할로 참여
              </Badge>

              {/* 수락 버튼 */}
              {isSignedIn ? (
                <Button
                  className="w-full cursor-pointer"
                  size="lg"
                  onClick={handleAccept}
                  disabled={acceptInvite.isPending}
                >
                  {acceptInvite.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      참여 중...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      워크스페이스 참여
                    </>
                  )}
                </Button>
              ) : (
                <div className="space-y-2">
                  <p
                    className="text-xs"
                    style={{ color: "var(--text-muted)" }}
                  >
                    참여하려면 먼저 로그인이 필요합니다
                  </p>
                  <SignInButton
                    mode="modal"
                    forceRedirectUrl={`/invite/${code}`}
                  >
                    <Button className="w-full cursor-pointer" size="lg">
                      로그인하고 참여
                    </Button>
                  </SignInButton>
                </div>
              )}

              {/* 에러 메시지 */}
              {acceptInvite.isError && (
                <p className="text-xs text-red-400">
                  {(acceptInvite.error as Error)?.message ??
                    "참여에 실패했습니다. 다시 시도해주세요."}
                </p>
              )}
            </>
          ) : (
            /* 무효한 초대 */
            <>
              <div className="space-y-1.5">
                <XCircle className="w-8 h-8 mx-auto text-red-400 mb-2" />
                <h1
                  className="text-lg font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  초대를 사용할 수 없습니다
                </h1>
                <p
                  className="text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {info?.reason ?? "초대 링크가 만료되었거나 존재하지 않습니다"}
                </p>
              </div>
              <Button
                variant="outline"
                className="w-full cursor-pointer"
                onClick={() => router.push("/")}
              >
                홈으로 돌아가기
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
