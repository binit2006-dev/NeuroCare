import { useEffect, useState } from "react";
import { fetchDownloads, downloadUrl } from "@/lib/api";
import { Download, FileText, Image as ImageIcon, File as FileIcon } from "lucide-react";
import { useLang } from "@/context/LanguageContext";

const iconFor = (ext) => {
  if (["png", "jpg", "jpeg", "webp"].includes(ext)) return ImageIcon;
  if (["pdf", "txt", "md"].includes(ext)) return FileText;
  return FileIcon;
};

const prettySize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function Downloads() {
  const { t } = useLang();
  const [files, setFiles] = useState(null);
  useEffect(() => { fetchDownloads().then(setFiles).catch(() => setFiles([])); }, []);

  return (
    <div className="relative">
      <section className="max-w-5xl mx-auto px-6 lg:px-10 pt-20 pb-12">
        <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium">{t("dl_small")}</p>
        <h1 className="mt-4 font-light text-4xl sm:text-5xl lg:text-6xl tracking-tight">
          {t("dl_title_1")} <span className="text-primary">{t("dl_title_2")}</span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-2xl leading-relaxed">
          {t("dl_sub_1")}
          <code className="mx-1 px-1.5 py-0.5 rounded bg-muted text-xs">/app/backend/downloads/</code>
          {t("dl_sub_2")}
        </p>
      </section>

      <section className="max-w-5xl mx-auto px-6 lg:px-10 pb-24">
        {files === null && <div className="text-muted-foreground">{t("loading")}</div>}
        {files && files.length === 0 && (
          <div data-testid="downloads-empty" className="rounded-2xl border border-dashed border-border bg-white p-10 text-center text-muted-foreground">
            {t("dl_empty")} <code className="mx-1 px-1.5 py-0.5 rounded bg-muted text-xs">/app/backend/downloads/</code>
          </div>
        )}
        {files && files.length > 0 && (
          <ul data-testid="downloads-list" className="grid sm:grid-cols-2 gap-4">
            {files.map((f) => {
              const Icon = iconFor(f.ext);
              return (
                <li
                  key={f.name}
                  data-testid={`download-${f.name}`}
                  className="rounded-xl bg-white border border-border p-5 flex items-center gap-4 hover:border-primary/40 hover:-translate-y-0.5"
                >
                  <span className="w-11 h-11 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-primary" strokeWidth={1.75} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{f.name}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{f.ext.toUpperCase()} · {prettySize(f.size_bytes)}</div>
                  </div>
                  <a
                    href={downloadUrl(f.name)}
                    download
                    data-testid={`download-link-${f.name}`}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary text-primary-foreground text-sm hover:bg-[#3a6347]"
                  >
                    <Download className="w-4 h-4" /> {t("dl_get")}
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
