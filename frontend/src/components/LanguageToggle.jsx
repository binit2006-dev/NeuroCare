import { Languages } from "lucide-react";
import { useLang } from "@/context/LanguageContext";

export default function LanguageToggle() {
  const { t, toggle } = useLang();
  return (
    <button
      data-testid="language-toggle"
      onClick={toggle}
      aria-label={t("lang_switch_aria")}
      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full border border-border bg-white text-sm hover:bg-primary/10 hover:border-primary/40"
    >
      <Languages className="w-4 h-4 text-primary" />
      {t("lang_switch")}
    </button>
  );
}
