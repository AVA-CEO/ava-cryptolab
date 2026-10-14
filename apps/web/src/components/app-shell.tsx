"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import {
  Activity,
  ArrowUpRight,
  Bell,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  GraduationCap,
  Menu,
  Moon,
  Search,
  Sun,
  X,
} from "lucide-react";
import { navigation } from "@/lib/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function subscribeViewport(callback: () => void) {
  const query = window.matchMedia("(max-width: 760px)");
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
}
function mobileSnapshot() {
  return window.matchMedia("(max-width: 760px)").matches;
}
function serverSnapshot() {
  return false;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [notifications, setNotifications] = useState(false);
  const isMobile = useSyncExternalStore(
    subscribeViewport,
    mobileSnapshot,
    serverSnapshot,
  );
  const sidebarRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!mobileOpen || !isMobile) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const controls = sidebarRef.current?.querySelectorAll<HTMLElement>(
      "a[href], button:not([disabled])",
    );
    const visible = Array.from(controls ?? []).filter(
      (element) => element.getClientRects().length > 0,
    );
    const first = visible[0];
    const last = visible.at(-1);
    first?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
      if (
        event.key === "Tab" &&
        event.shiftKey &&
        document.activeElement === first
      ) {
        event.preventDefault();
        last?.focus();
      }
      if (
        event.key === "Tab" &&
        !event.shiftKey &&
        document.activeElement === last
      ) {
        event.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [mobileOpen, isMobile]);
  const page = navigation.find((n) => n.href === path)?.label ?? "Workspace";
  const matches = search.trim()
    ? navigation.filter((n) =>
        n.label.toLowerCase().includes(search.toLowerCase()),
      )
    : [];
  return (
    <div className={cn("app-shell", collapsed && "is-collapsed")}>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      {mobileOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        id="workspace-navigation"
        ref={sidebarRef}
        inert={isMobile && !mobileOpen}
        role={isMobile && mobileOpen ? "dialog" : undefined}
        aria-modal={isMobile && mobileOpen ? true : undefined}
        className={cn("sidebar", mobileOpen && "mobile-open")}
        aria-label="Main navigation"
      >
        <Link className="brand" href="/" onClick={() => setMobileOpen(false)}>
          <span className="brand-mark">
            <Activity size={25} strokeWidth={2.5} />
          </span>
          <span className="brand-copy">
            <strong>
              AVA<span>CryptoLab</span>
            </strong>
            <small>ANALYSE. LEARN. TRADE SMARTER.</small>
          </span>
        </Link>
        <div className="nav-caption">YOUR WORKSPACE</div>
        <nav>
          {navigation.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              title={collapsed ? n.label : undefined}
              aria-current={path === n.href ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
              className={cn("nav-item", path === n.href && "active")}
            >
              <n.icon size={19} />
              <span>{n.label}</span>
              {n.href === "/trivia" && <small>SOON</small>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="journey-card">
            <span className="journey-icon">
              <GraduationGlyph />
            </span>
            <strong>A little wiser, every day.</strong>
            <p>Your edge starts with understanding.</p>
            <Link href="/academy">
              Explore the academy <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="local-profile">
            <span className="avatar">A</span>
            <div>
              <strong>Personal workspace</strong>
              <small>Local development</small>
            </div>
            <span className="status-dot" />
          </div>
          <Button
            variant="ghost"
            className="collapse-button"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronsRight size={17} />
            ) : (
              <>
                <ChevronsLeft size={17} />
                <span>Collapse sidebar</span>
              </>
            )}
          </Button>
        </div>
      </aside>
      <div className="workspace" inert={isMobile && mobileOpen}>
        <header className="topbar">
          <div className="breadcrumb">
            <Button
              variant="ghost"
              size="icon"
              className="mobile-menu"
              aria-label="Open navigation"
              aria-controls="workspace-navigation"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={20} />
            </Button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>
          <div className="topbar-actions">
            <div className="global-search">
              <Search size={16} />
              <input
                aria-label="Search workspace"
                placeholder="Search workspace…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Clear search"
                  onClick={() => setSearch("")}
                >
                  <X size={14} />
                </Button>
              )}
              {search.trim() && (
                <div className="search-results">
                  {matches.length ? (
                    matches.map((n) => (
                      <Link
                        key={n.href}
                        href={n.href}
                        onClick={() => setSearch("")}
                      >
                        <n.icon size={16} />
                        {n.label}
                      </Link>
                    ))
                  ) : (
                    <p>No matching modules.</p>
                  )}
                </div>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Toggle color theme"
              onClick={() =>
                setTheme(resolvedTheme === "dark" ? "light" : "dark")
              }
            >
              <Sun size={18} className="dark-sun" />
              <Moon size={18} className="light-moon" />
            </Button>
            <div className="notification-wrap">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Notifications"
                aria-expanded={notifications}
                onClick={() => setNotifications(!notifications)}
              >
                <Bell size={18} />
              </Button>
              {notifications && (
                <div className="notification-panel" role="status">
                  <strong>You’re all caught up</strong>
                  <p>
                    Learning reminders and account notifications arrive in a
                    later phase.
                  </p>
                </div>
              )}
            </div>
            <span
              className="top-avatar avatar"
              title="Local personal workspace"
            >
              A
            </span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <footer className="workspace-footer">
          <span>
            AVA CryptoLab <span className="footer-dot">·</span> Analyse. Learn.
            Trade Smarter.
          </span>
          <span>
            Research & education <span className="footer-dot">·</span> Phase 1
          </span>
        </footer>
      </div>
    </div>
  );
}
function GraduationGlyph() {
  return <GraduationCap size={20} />;
}
