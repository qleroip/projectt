import type { ExpertUser } from "../lib/types";
import { roleLabels } from "../lib/labels";
import { cn } from "../lib/utils";
import { Button } from "./ui";

export type Page = "risks" | "assessments" | "profile";

export function Sidebar({
  user,
  page,
  onPage,
  onLogout,
}: {
  user: ExpertUser;
  page: Page;
  onPage: (page: Page) => void;
  onLogout: () => void;
}) {
  const initials = user.full_name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <aside className="sidebar">
      <div className="flex items-center gap-3 border-b border-[#2a3b5d] p-5">
        <img className="h-14 w-14 object-contain" src="/guard.png" alt="RiskGuard" />
        <div>
          <div className="text-xl font-extrabold text-white">RiskGuard</div>
          <div className="text-sm text-[#a9bcdf]">Экспертная панель</div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-2 p-4">
        <button className={cn("sidebar-link", page === "risks" && "active")} onClick={() => onPage("risks")}>
          Назначенные риски
        </button>
        <button className={cn("sidebar-link", page === "assessments" && "active")} onClick={() => onPage("assessments")}>
          Оценки
        </button>
        <button className={cn("sidebar-link", page === "profile" && "active")} onClick={() => onPage("profile")}>
          Профиль
        </button>
      </nav>

      <div className="space-y-3 p-4">
        <div className="flex items-center gap-3 rounded-lg border border-white/15 bg-white/10 p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-extrabold text-white">
            {initials || "RG"}
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-bold text-white">{user.full_name}</div>
            <div className="text-xs text-[#bed0f3]">{roleLabels[user.role]}</div>
          </div>
        </div>
        <Button className="w-full justify-start text-[#dbe6ff]" onClick={onLogout} variant="ghost">
          Выйти
        </Button>
      </div>
    </aside>
  );
}
