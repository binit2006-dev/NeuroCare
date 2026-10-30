import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Brain } from "lucide-react";
import { useEffect } from "react";
import UserMenu from "@/components/UserMenu";
import LanguageToggle from "@/components/LanguageToggle";
import { useLang } from "@/context/LanguageContext";

const nav = [
  { to: "/", key: "nav_scan", id: "scan" },
  { to: "/history", key: "nav_history", id: "my-scans" },
  { to: "/about", key: "nav_about", id: "about-pinn" },
  { to: "/downloads", key: "nav_downloads", id: "downloads" },
];

export default function Layout() {
  const { pathname } = useLocation();
  const { t } = useLang();
  useEffect(() => { window.scrollTo({ top: 0, behavior: "instant" }); }, [pathname]);

  return (
    <div className="min-h-screen flex flex-col">
      <header
        data-testid="site-header"
        className="sticky top-0 z-40 bg-[#FDFBF7]/75 backdrop-blur-xl border-b border-border/60"
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
          <Link to="/" data-testid="brand-link" className="flex items-center gap-2.5 group">
            <span className="w-9 h-9 rounded-md bg-primary/10 flex items-center justify-center group-hover:bg-primary/15">
              <Brain className="w-5 h-5 text-primary" strokeWidth={1.75} />
            </span>
            <span className="font-medium tracking-tight text-[17px]">
              Neuro<span className="text-primary">Care</span>
            </span>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                data-testid={`nav-${n.id}`}
                className={({ isActive }) =>
                  `px-3 sm:px-4 py-2 rounded-full text-sm hover:bg-primary/10 ${
                    isActive ? "bg-primary/10 text-primary" : "text-foreground/80"
                  }`
                }
                end={n.to === "/"}
              >
                {t(n.key)}
              </NavLink>
            ))}
            <LanguageToggle />
            <UserMenu />
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer data-testid="site-footer" className="border-t border-border/60 mt-24">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} NeuroCare. {t("footer_disclaimer")}</p>
          <p className="text-xs">{t("footer_built")}</p>
        </div>
      </footer>
    </div>
  );
}
