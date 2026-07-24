import Link from "next/link";
import { Activity, BarChart3, BookOpenText, Bot, BriefcaseBusiness, Building2, CalendarClock, ClipboardCheck, Cog, FileAudio, Headphones, Inbox, KeyRound, Link2, MessageCircle, PhoneCall, Radio, Route, ScrollText, Shield, Users } from "lucide-react";
import { MenuPayload } from "@/lib/types";
import { cn } from "@/lib/utils";

const icons: Record<string, React.ComponentType<{ className?: string }>> = {
  overview: BarChart3,
  "live-desk": Headphones,
  "webrtc-phone": Radio,
  "active-calls": PhoneCall,
  queues: Activity,
  numbers: Route,
  recordings: FileAudio,
  scripts: ScrollText,
  conversations: MessageCircle,
  contacts: Users,
  opportunities: BriefcaseBusiness,
  "follow-ups": CalendarClock,
  inboxes: Inbox,
  chatwoot: Inbox,
  webchat: MessageCircle,
  whatsapp: MessageCircle,
  transcriptions: BookOpenText,
  quality: ClipboardCheck,
  reports: BarChart3,
  integrations: Link2,
  "service-levels": Bot,
  tenants: Building2,
  users: Users,
  roles: Shield,
  audit: KeyRound,
  security: KeyRound
};

const bubbleClasses: Record<string, string> = {
  overview: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  "live-desk": "bg-[var(--teal-bg)] text-[var(--teal-text)]",
  "webrtc-phone": "bg-[var(--purple-bg)] text-[var(--purple-text)]",
  "active-calls": "bg-[var(--teal-bg)] text-[var(--teal-text)]",
  queues: "bg-[var(--green-bg)] text-[var(--green-text)]",
  recordings: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  scripts: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
  contacts: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  opportunities: "bg-[var(--green-bg)] text-[var(--green-text)]",
  "follow-ups": "bg-[var(--amber-bg)] text-[var(--amber-text)]",
  inboxes: "bg-[var(--teal-bg)] text-[var(--teal-text)]",
  chatwoot: "bg-[var(--green-bg)] text-[var(--green-text)]",
  webchat: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  whatsapp: "bg-[var(--teal-bg)] text-[var(--teal-text)]",
  numbers: "bg-[var(--coral-bg)] text-[var(--coral-text)]",
  transcriptions: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  quality: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
  reports: "bg-[var(--green-bg)] text-[var(--green-text)]",
  integrations: "bg-[var(--purple-bg)] text-[var(--purple-text)]",
  conversations: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  "service-levels": "bg-[var(--teal-bg)] text-[var(--teal-text)]",
  tenants: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  users: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
  roles: "bg-[var(--purple-bg)] text-[var(--purple-text)]",
  audit: "bg-[var(--coral-bg)] text-[var(--coral-text)]"
};

export function Sidebar({
  menu,
  currentPath,
  collapsed = false
}: {
  menu: MenuPayload;
  currentPath: string;
  collapsed?: boolean;
}) {
  return (
    <aside className={cn("sticky top-0 flex h-screen shrink-0 flex-col border-r bg-surface shadow-[1px_0_0_var(--shadow-color)] transition-[width]", collapsed ? "w-16" : "w-72")}>
      <div className={cn("border-b py-4", collapsed ? "px-2 text-center" : "px-5")}>
        <div className={cn("font-semibold tracking-normal text-foreground", collapsed ? "text-body-sm" : "text-section-title")}>{collapsed ? "VX" : "Voxalia"}</div>
        {!collapsed ? <div className="mt-1 text-body-sm text-muted-foreground">Service Console</div> : null}
      </div>
      <nav className={cn("flex-1 overflow-y-auto py-4", collapsed ? "px-2" : "px-3")}>
        {menu.sections.map((section) => (
          <div key={section.id} className="mb-5">
            <div className={cn("mb-2 px-2 text-meta font-normal uppercase tracking-[0.08em] text-ink-muted", collapsed && "sr-only")}>
              {section.label}
            </div>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = icons[item.id] ?? Cog;
                const active = currentPath === item.href;
                const bubbleClass = bubbleClasses[item.id] ?? "bg-[var(--surface-3)] text-[var(--ink-secondary)]";
                return (
                  <Link
                    key={item.id}
                    href={item.href}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      "flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-body-sm transition-colors",
                      collapsed && "justify-center px-0",
                      active
                        ? "bg-[var(--nav-active)] text-[var(--nav-active-foreground)] shadow-[0_1px_2px_var(--shadow-color)]"
                        : "text-ink-secondary hover:bg-surface-hover hover:text-foreground"
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-[5px] transition-colors",
                        active ? "bg-[var(--nav-active-icon-bg)] text-[var(--nav-active-foreground)]" : bubbleClass
                      )}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                    </span>
                    {!collapsed ? <span className="truncate">{item.label}</span> : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
