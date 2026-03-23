"use client";

import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useUIStore } from "@/store/ui";
import { Sidebar } from "./sidebar";

export function MobileSidebar() {
  const isOpen = useUIStore((s) => s.isSidebarOpen);
  const setOpen = useUIStore((s) => s.setSidebarOpen);

  return (
    <Sheet open={isOpen} onOpenChange={setOpen}>
      <SheetContent side="left" className="w-64 p-0">
        <Sidebar />
      </SheetContent>
    </Sheet>
  );
}
