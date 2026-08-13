// 로딩 자리표시자 — 펄스 placeholder (shadcn Skeleton 프리미티브)
import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn(
        "animate-pulse rounded-md bg-[var(--surface-active)]",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
