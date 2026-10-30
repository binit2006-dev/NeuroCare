import { ArrowDown, Sparkles } from "lucide-react";
import { useLang } from "@/context/LanguageContext";

export default function Hero({ onCta }) {
  const { t } = useLang();
  return (
    <section data-testid="hero-section" className="relative overflow-hidden">
      {/* Organic abstract shapes */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-24 -right-24 w-[520px] h-[520px] rounded-full bg-secondary/40 blur-3xl drift" />
        <div className="absolute top-40 -left-32 w-[420px] h-[420px] rounded-full bg-accent/30 blur-3xl drift" style={{ animationDelay: "-5s" }} />
        <div className="absolute bottom-0 left-1/3 w-[380px] h-[380px] rounded-full bg-primary/15 blur-3xl drift" style={{ animationDelay: "-9s" }} />
      </div>

      <div className="max-w-7xl mx-auto px-6 lg:px-10 pt-20 pb-24 lg:pt-28 lg:pb-32 grid lg:grid-cols-12 gap-10 items-center">
        <div className="lg:col-span-7">
          <span data-testid="hero-tag" className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-border/70 text-xs text-muted-foreground">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            {t("hero_tag")}
          </span>

          <h1 data-testid="hero-title" className="mt-6 font-light tracking-tight text-4xl sm:text-5xl lg:text-6xl leading-[1.05]">
            {t("hero_title_1")} <br className="hidden sm:block" />
            <span className="text-primary font-medium">{t("hero_title_2")}</span>
          </h1>

          <p className="mt-6 text-base sm:text-lg text-muted-foreground max-w-xl leading-relaxed">
            {t("hero_sub")}
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <button
              data-testid="hero-cta-start"
              onClick={onCta}
              className="group inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-primary text-primary-foreground hover:bg-[#3a6347] hover:-translate-y-[1px]"
            >
              {t("hero_cta")}
              <ArrowDown className="w-4 h-4 group-hover:translate-y-0.5" />
            </button>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <div className="flex -space-x-2">
                <span className="w-7 h-7 rounded-full bg-primary/20 border-2 border-background" />
                <span className="w-7 h-7 rounded-full bg-secondary/80 border-2 border-background" />
                <span className="w-7 h-7 rounded-full bg-accent/70 border-2 border-background" />
              </div>
              <span>{t("hero_private")}</span>
            </div>
          </div>
        </div>

        <div className="lg:col-span-5 relative">
          <div className="relative aspect-square max-w-md mx-auto">
            <div className="absolute inset-0 rounded-[2rem] overflow-hidden shadow-[0_30px_80px_-30px_rgba(74,124,89,0.35)]">
              <img
                src="https://images.unsplash.com/photo-1761888856976-c4bc8303f65f?crop=entropy&cs=srgb&fm=jpg&q=85&w=800"
                alt="Soft calming abstract"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="absolute -bottom-6 -left-6 bg-white border border-border rounded-xl px-5 py-4 shadow-xl max-w-[220px]">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">{t("hero_model")}</div>
              <div className="font-medium mt-1">{t("hero_model_name")}</div>
              <div className="text-xs text-muted-foreground mt-1.5">{t("hero_model_classes")}</div>
            </div>
            <div className="absolute -top-5 -right-4 bg-primary text-primary-foreground rounded-xl px-4 py-3 shadow-xl">
              <div className="text-xs opacity-80">{t("hero_powered")}</div>
              <div className="font-medium">GPT 6 Sol</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
