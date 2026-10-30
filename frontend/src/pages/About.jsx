import { useEffect, useState } from "react";
import { fetchModelStatus } from "@/lib/api";
import { Atom, Database, Shield, Sparkles, FolderOpen } from "lucide-react";
import { useLang } from "@/context/LanguageContext";

const C = ({ children }) => <code className="px-1.5 py-0.5 rounded bg-muted text-xs">{children}</code>;

export default function About() {
  const { t } = useLang();
  const [status, setStatus] = useState(null);
  useEffect(() => { fetchModelStatus().then(setStatus).catch(() => {}); }, []);

  return (
    <div className="relative">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-32 right-10 w-[520px] h-[520px] rounded-full bg-accent/25 blur-3xl drift" />
      </div>

      <section className="max-w-5xl mx-auto px-6 lg:px-10 pt-20 pb-10">
        <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium">{t("about_small")}</p>
        <h1 className="mt-4 font-light text-4xl sm:text-5xl lg:text-6xl tracking-tight">
          {t("about_title_1")} <span className="text-primary">{t("about_title_2")}</span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-2xl leading-relaxed">
          {t("about_intro")}
        </p>
      </section>

      <section className="max-w-6xl mx-auto px-6 lg:px-10 grid md:grid-cols-3 gap-5 pb-12">
        {[
          { icon: Atom, title: t("f1_title"), text: t("f1_text") },
          { icon: Database, title: t("f2_title"), text: t("f2_text") },
          { icon: Shield, title: t("f3_title"), text: t("f3_text") },
        ].map(({ icon: Icon, title, text }) => (
          <div key={title} className="rounded-2xl bg-white border border-border p-6">
            <Icon className="w-6 h-6 text-primary" strokeWidth={1.75} />
            <div className="mt-4 font-medium">{title}</div>
            <p className="mt-2 text-sm text-muted-foreground">{text}</p>
          </div>
        ))}
      </section>

      <section className="max-w-5xl mx-auto px-6 lg:px-10 pb-20">
        <div className="rounded-2xl border border-border bg-white overflow-hidden">
          <div className="grid md:grid-cols-5">
            <div className="md:col-span-2 min-h-[260px]">
              <img
                src="https://images.unsplash.com/photo-1761888857230-1659946aaa8b?crop=entropy&cs=srgb&fm=jpg&q=85&w=800"
                alt="Abstract blue waves representing AI"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="md:col-span-3 p-8">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-primary">
                <FolderOpen className="w-4 h-4" /> {t("plug_small")}
              </div>
              <h2 className="mt-3 font-light text-2xl sm:text-3xl tracking-tight">
                {t("plug_title")}
              </h2>
              <ol className="mt-5 space-y-3 text-sm">
                <li className="flex gap-3">
                  <span className="w-6 h-6 flex-shrink-0 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-medium">1</span>
                  <div>{t("plug_1")} <C>/app/backend/models/</C></div>
                </li>
                <li className="flex gap-3">
                  <span className="w-6 h-6 flex-shrink-0 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-medium">2</span>
                  <div>{t("plug_2")} <C>pinn_model.pth</C>, <C>.pt</C>, <C>.h5</C>, <C>.onnx</C></div>
                </li>
                <li className="flex gap-3">
                  <span className="w-6 h-6 flex-shrink-0 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-medium">3</span>
                  <div>{t("plug_3")} <C>pinn_predictor.py</C></div>
                </li>
              </ol>

              <div className="mt-6 rounded-lg bg-muted/60 p-4 text-sm">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <span className="font-medium">{t("status_title")}</span>
                </div>
                {status ? (
                  <div data-testid="model-status" className="mt-2 grid grid-cols-2 gap-y-1 text-xs">
                    <span className="text-muted-foreground">{t("status_loaded")}</span>
                    <span>{status.model_loaded ? t("yes") : t("no_demo")}</span>
                    <span className="text-muted-foreground">{t("model_file")}</span>
                    <span>{status.model_file || "—"}</span>
                    <span className="text-muted-foreground">{t("classes")}</span>
                    <span>{status.classes?.join(" · ")}</span>
                  </div>
                ) : (
                  <div className="mt-2 text-xs text-muted-foreground">{t("checking")}</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
