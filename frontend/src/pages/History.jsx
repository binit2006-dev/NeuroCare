import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { History as HistoryIcon, LogIn, ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { fetchMyScans } from "@/lib/api";
import { useLang } from "@/context/LanguageContext";

function SignInPrompt({ login }) {
  const { t } = useLang();
  return (
    <div data-testid="history-signin-prompt" className="rounded-2xl border border-border bg-white p-10 max-w-xl">
      <h2 className="font-light text-2xl tracking-tight">{t("hist_signin_title")}</h2>
      <p className="mt-3 text-muted-foreground">{t("hist_signin_sub")}</p>
      <button data-testid="history-signin-button" onClick={login} className="mt-6 inline-flex items-center gap-2 px-5 py-3 rounded-full bg-primary text-primary-foreground hover:bg-[#3a6347]">
        <LogIn className="w-4 h-4" /> {t("hist_signin_btn")}
      </button>
    </div>
  );
}

function ScanCard({ s }) {
  const { t, lang } = useLang();
  const advice = (lang === "hi" && s.advice_hi) || s.advice;
  return (
    <li data-testid={`history-item-${s.id}`} className="rounded-xl bg-white border border-border p-5 hover:border-primary/40 hover:-translate-y-0.5">
      <div className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleString(lang === "hi" ? "hi-IN" : undefined)}</div>
      <div className={`mt-1 font-medium ${s.tumor_detected ? "" : "text-primary"}`}>{t(`class_${s.tumor_type}`)}</div>
      <div className="mt-2 text-sm text-muted-foreground">
        {(s.confidence * 100).toFixed(1)}% {t("hist_conf")} · {s.location || t("hist_no_location")}
      </div>
      {advice?.tumor_info?.overview && <p className="mt-3 text-sm text-foreground/80 line-clamp-3">{advice.tumor_info.overview}</p>}
    </li>
  );
}

export default function History() {
  const { user, loading, login } = useAuth();
  const { t } = useLang();
  const [scans, setScans] = useState(null);

  useEffect(() => {
    if (user) fetchMyScans().then(setScans).catch(() => setScans([]));
  }, [user]);

  return (
    <section className="max-w-5xl mx-auto px-6 lg:px-10 pt-20 pb-24">
      <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium flex items-center gap-2">
        <HistoryIcon className="w-4 h-4" /> {t("hist_small")}
      </p>
      <h1 className="mt-4 font-light text-4xl sm:text-5xl lg:text-6xl tracking-tight">
        {user ? <>{t("hist_hello")} <span className="text-primary">{user.name.split(" ")[0]}.</span></> : t("hist_title")}
      </h1>
      <div className="mt-10">
        {loading ? null : !user ? <SignInPrompt login={login} /> : scans === null ? (
          <div className="text-muted-foreground">{t("loading")}</div>
        ) : scans.length === 0 ? (
          <div data-testid="history-empty" className="rounded-2xl border border-dashed border-border bg-white p-10 text-muted-foreground">
            {t("hist_empty")}
            <Link to="/" data-testid="history-start-scan" className="ml-2 inline-flex items-center gap-1 text-primary hover:underline">
              {t("hist_start")} <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <ul data-testid="history-list" className="grid sm:grid-cols-2 gap-4">
            {scans.map((s) => <ScanCard key={s.id} s={s} />)}
          </ul>
        )}
      </div>
    </section>
  );
}
