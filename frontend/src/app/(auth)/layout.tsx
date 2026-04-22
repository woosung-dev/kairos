import { ThemeProvider } from "@/components/layout/theme-provider";
import { QueryProvider } from "@/lib/query-client";
import { Toaster } from "@/components/ui/sonner";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryProvider>
        {children}
        <Toaster />
      </QueryProvider>
    </ThemeProvider>
  );
}
