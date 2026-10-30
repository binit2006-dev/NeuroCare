import { useState } from "react";
import { Flame } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { useLang } from "@/context/LanguageContext";

export default function HeatmapViewer({ scan }) {
  const { t } = useLang();
  const [show, setShow] = useState(true);
  const [opacity, setOpacity] = useState(85);
  if (!scan.preview || !scan.heatmap) return null;

  const area = scan.tumor_area_pct ?? 0;
  const highlighted = area > 0.05;

  return (
    <div data-testid="heatmap-card" className="mt-8 grid lg:grid-cols-12 gap-6 items-center rounded-2xl bg-white border border-border p-6 sm:p-8">
      <div className="lg:col-span-6">
        <div className="relative mx-auto max-w-md rounded-xl overflow-hidden bg-black">
          <img data-testid="heatmap-base-image" src={scan.preview} alt="Uploaded MRI scan" className="w-full h-auto block" />
          <img
            data-testid="heatmap-overlay"
            src={scan.heatmap}
            alt="Predicted tumor region"
            className="absolute inset-0 w-full h-full heatmap-glow pointer-events-none"
            style={{ opacity: show ? opacity / 100 : 0, transition: "opacity 0.5s ease" }}
          />
        </div>
      </div>
      <div className="lg:col-span-6">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-primary">
          <Flame className="w-4 h-4" /> {t("hm_small")}
        </div>
        <h3 className="mt-3 font-light text-2xl tracking-tight">
          {highlighted ? t("hm_title_yes") : t("hm_title_no")}
        </h3>
        <p className="mt-3 text-sm text-foreground/80 leading-relaxed">
          {highlighted ? t("hm_desc_yes") : t("hm_desc_no")}
        </p>
        <div data-testid="tumor-area-pct" className="mt-5 inline-flex items-baseline gap-2 rounded-lg bg-secondary/25 px-4 py-2">
          <span className="text-2xl font-light">{area.toFixed(1)}%</span>
          <span className="text-xs text-muted-foreground">{t("hm_area")}</span>
        </div>
        <div className="mt-6 space-y-4">
          <label className="flex items-center justify-between gap-4 text-sm">
            <span>{t("hm_show")}</span>
            <Switch data-testid="heatmap-toggle" checked={show} onCheckedChange={setShow} />
          </label>
          <div className={show ? "" : "opacity-40 pointer-events-none"}>
            <div className="flex justify-between text-sm mb-2">
              <span>{t("hm_intensity")}</span>
              <span className="text-muted-foreground">{opacity}%</span>
            </div>
            <Slider data-testid="heatmap-opacity-slider" value={[opacity]} min={10} max={100} step={5} onValueChange={(v) => setOpacity(v[0])} />
          </div>
        </div>
      </div>
    </div>
  );
}
