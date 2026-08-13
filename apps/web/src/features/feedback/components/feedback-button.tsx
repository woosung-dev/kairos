"use client";
// 우하단 floating 피드백 버튼 + 제출 모달 (Sprint 28 Wave 1 dogfooding)
import { useState } from "react";
import { usePathname } from "next/navigation";
import { MessageSquarePlus, Star } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useWorkspaceStore } from "@/features/workspaces/store";
import { useSubmitFeedback } from "../hooks";

export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [rating, setRating] = useState<number | null>(null);
  const [isAnonymous, setIsAnonymous] = useState(false);

  const pathname = usePathname();
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const submit = useSubmitFeedback();

  const reset = () => {
    setBody("");
    setRating(null);
    setIsAnonymous(false);
  };

  const handleSubmit = () => {
    if (!body.trim()) return;
    submit.mutate(
      {
        body: body.trim(),
        rating,
        isAnonymous,
        workspaceId: activeWorkspaceId,
        pageUrl: pathname,
      },
      {
        onSuccess: () => {
          toast.success(
            "피드백 감사합니다! 더 나은 Kairos 를 만드는 데 큰 힘이 됩니다.",
          );
          setOpen(false);
          reset();
        },
        onError: (e: Error) =>
          toast.error(e.message || "피드백 전송에 실패했습니다"),
      },
    );
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="피드백 보내기"
        className="fixed right-4 z-30 flex h-11 w-11 items-center justify-center rounded-full shadow-lg transition-transform hover:scale-105 bottom-[calc(var(--bottom-nav-height)+1rem)] md:bottom-6"
        style={{ background: "var(--accent)", color: "var(--accent-foreground)" }}
      >
        <MessageSquarePlus size={20} />
      </button>

      <Dialog
        open={open}
        onOpenChange={(o) => {
          setOpen(o);
          if (!o) reset();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>피드백 보내기</DialogTitle>
            <DialogDescription>
              버그·불편·아이디어 무엇이든 좋습니다. 베타 기간 여러분의 의견이 제품을 만듭니다.
            </DialogDescription>
          </DialogHeader>

          {/* 만족도 별점 (선택) */}
          <div
            className="flex items-center gap-1"
            role="radiogroup"
            aria-label="만족도 별점 (선택)"
          >
            {[1, 2, 3, 4, 5].map((n) => {
              const filled = rating !== null && n <= rating;
              return (
                <button
                  key={n}
                  type="button"
                  aria-label={`${n}점`}
                  aria-pressed={rating === n}
                  onClick={() => setRating(rating === n ? null : n)}
                  className="p-0.5 transition-transform hover:scale-110"
                  style={{ color: filled ? "var(--accent)" : "var(--text-muted)" }}
                >
                  <Star size={22} fill={filled ? "currentColor" : "none"} />
                </button>
              );
            })}
          </div>

          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="무엇이 좋았나요? 어떤 점이 불편했나요?"
            rows={5}
            maxLength={5000}
            autoFocus
          />

          <label
            className="flex items-center gap-2 text-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            <input
              type="checkbox"
              checked={isAnonymous}
              onChange={(e) => setIsAnonymous(e.target.checked)}
              style={{ accentColor: "var(--accent)" }}
            />
            익명으로 보내기
          </label>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              취소
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!body.trim() || submit.isPending}
            >
              {submit.isPending ? "보내는 중…" : "보내기"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
