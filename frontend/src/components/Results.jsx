import { useEffect, useState } from "react";
import { fetchAdvice } from "@/lib/api";
import { CheckCircle2, Info, Phone, Hospital, UserRound, Sparkles, RefreshCcw, AlertCircle } from "lucide-react";
import { toast } from "sonner";

const TUMOR_LABEL = {
  no_tumor: "No tumor detected",
  glioma: "Glioma (suspected)",
  meningioma: "Meningioma (suspected)",
  pituitary: "Pituitary (suspected)",
};

export default function Results({ scan, onReset }) {
  const [advice, setAdvice] = useState(null);
  const [loadingAdvice, setLoadingAdvice] = useState(true);
  const [adviceError, setAdviceError] = useState(null);

  const loadAdvice = async () => {
    try {
      setLoadingAdvice(true);
      setAdviceError(null);
      const data = await fetchAdvice(scan);
      setAdvice(data);
    } catch (err) {
      setAdviceError(err?.response?.data?.detail || "Could not fetch guidance.");
    } finally {
      setLoadingAdvice(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadAdvice(); }, [scan.id]);

  const positive = !scan.tumor_detected;
  const headlineBg = positive ? "bg-primary/10" : "bg-secondary/30";
  const headlineText = positive ? "text-primary" : "text-foreground";

  return (
    <section data-testid="results-section" className="py-16">
      <div className="max-w-6xl mx-auto px-6 lg:px-10">
        {scan.demo_mode && (
          <div data-testid="demo-mode-banner" className="mb-6 flex items-center gap-3 rounded-lg border border-secondary/60 bg-secondary/20 px-4 py-3 text-sm">
            <Info className="w-4 h-4 text-foreground/70 flex-shrink-0" />
            Demo mode is active — drop your trained PINN model file into
            <code className="mx-1 px-1.5 py-0.5 rounded bg-white border text-xs">/app/backend/models/</code>
            to use real predictions.
          </div>
        )}

        {/* Verdict */}
        <div className={`rounded-2xl ${headlineBg} border border-border/60 p-8 sm:p-10`}>
          <div className="flex items-center gap-2.5 text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {positive ? <CheckCircle2 className="w-4 h-4 text-primary" /> : <Info className="w-4 h-4" />}
            MRI analysis result
          </div>
          <h2 className={`mt-4 font-light text-3xl sm:text-4xl lg:text-5xl tracking-tight ${headlineText}`}>
            {TUMOR_LABEL[scan.tumor_type] || scan.tumor_type}
          </h2>
          <div className="mt-5 flex flex-wrap items-center gap-6 text-sm">
            <div>
              <div className="text-muted-foreground">Model confidence</div>
              <div className="font-medium text-lg mt-0.5">{(scan.confidence * 100).toFixed(1)}%</div>
            </div>
            <div className="h-10 w-px bg-border" />
            <div>
              <div className="text-muted-foreground">File</div>
              <div className="font-medium mt-0.5 truncate max-w-[220px]">{scan.filename}</div>
            </div>
            <div className="h-10 w-px bg-border hidden sm:block" />
            <div className="hidden sm:block">
              <div className="text-muted-foreground">Location</div>
              <div className="font-medium mt-0.5">{scan.location || "—"}</div>
            </div>
            <button
              data-testid="reset-button"
              onClick={onReset}
              className="ml-auto inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-border hover:bg-muted text-sm"
            >
              <RefreshCcw className="w-3.5 h-3.5" /> New scan
            </button>
          </div>

          {/* class probabilities */}
          <div className="mt-8 grid sm:grid-cols-4 gap-3">
            {Object.entries(scan.class_probabilities).map(([k, v]) => (
              <div key={k} data-testid={`prob-${k}`} className="bg-white border border-border rounded-lg px-4 py-3">
                <div className="text-xs text-muted-foreground capitalize">{k.replace("_", " ")}</div>
                <div className="mt-1 font-medium">{(v * 100).toFixed(1)}%</div>
                <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{ width: `${v * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI advice */}
        {loadingAdvice && (
          <div data-testid="advice-loading" className="mt-10 flex items-center gap-3 text-muted-foreground">
            <Sparkles className="w-4 h-4 text-primary breathe" />
            Gathering personalised guidance from GPT 6 Sol…
          </div>
        )}

        {adviceError && (
          <div data-testid="advice-error" className="mt-10 flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-5 text-sm">
            <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium">We couldn&apos;t load the guidance.</div>
              <div className="text-muted-foreground mt-1">{adviceError}</div>
              <button data-testid="retry-advice-button" onClick={loadAdvice} className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary text-primary-foreground text-sm">
                Try again
              </button>
            </div>
          </div>
        )}

        {advice && (
          <div className="mt-12 grid lg:grid-cols-12 gap-6">
            {/* Tumor info */}
            <div data-testid="tumor-info-card" className="lg:col-span-7 bg-white rounded-2xl border border-border p-7">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-primary">
                <Info className="w-4 h-4" /> About this result
              </div>
              <h3 className="mt-3 font-light text-2xl tracking-tight">{advice.tumor_info?.name}</h3>
              <p className="mt-3 text-foreground/80 leading-relaxed">{advice.tumor_info?.overview}</p>
              {advice.tumor_info?.common_symptoms?.length > 0 && (
                <>
                  <div className="mt-6 text-sm font-medium text-muted-foreground">Common symptoms to be aware of</div>
                  <ul className="mt-2 grid sm:grid-cols-2 gap-2">
                    {advice.tumor_info.common_symptoms.map((s, i) => (
                      <li key={i} className="text-sm flex gap-2 items-start">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" /> {s}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {advice.tumor_info?.severity_note && (
                <div className="mt-5 rounded-lg bg-secondary/20 border border-secondary/50 p-4 text-sm">
                  {advice.tumor_info.severity_note}
                </div>
              )}
            </div>

            {/* Emergency */}
            <div data-testid="emergency-card" className="lg:col-span-5 bg-foreground text-background rounded-2xl p-7">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-background/70">
                <Phone className="w-4 h-4" /> Emergency contacts
              </div>
              <h3 className="mt-3 font-light text-2xl tracking-tight">Save these numbers</h3>
              <div className="mt-5 space-y-3">
                {advice.emergency_contacts?.map((c, i) => (
                  <a
                    key={i}
                    href={`tel:${c.number}`}
                    data-testid={`emergency-contact-${i}`}
                    className="flex items-center justify-between gap-3 rounded-lg bg-background/10 hover:bg-background/15 px-4 py-3"
                  >
                    <span className="text-sm text-background/80">{c.label}</span>
                    <span className="font-medium">{c.number}</span>
                  </a>
                ))}
              </div>
            </div>

            {/* Hospitals */}
            {advice.nearby_hospitals?.length > 0 && (
              <div data-testid="hospitals-card" className="lg:col-span-12 bg-white rounded-2xl border border-border p-7">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-primary">
                      <Hospital className="w-4 h-4" /> Nearby hospitals
                    </div>
                    <h3 className="mt-3 font-light text-2xl tracking-tight">Trusted places to start</h3>
                  </div>
                  {scan.location && (
                    <span className="text-sm text-muted-foreground">Based on: {scan.location}</span>
                  )}
                </div>
                <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {advice.nearby_hospitals.map((h, i) => (
                    <div key={i} data-testid={`hospital-${i}`} className="rounded-xl border border-border/70 p-5 hover:border-primary/40 hover:-translate-y-0.5">
                      <div className="text-xs text-muted-foreground">{h.city}</div>
                      <div className="font-medium mt-1 leading-tight">{h.name}</div>
                      <div className="text-xs text-primary mt-2">{h.specialty}</div>
                      <div className="text-sm text-muted-foreground mt-3">{h.notes}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Specialists */}
            {advice.recommended_specialists?.length > 0 && (
              <div data-testid="specialists-card" className="lg:col-span-7 bg-white rounded-2xl border border-border p-7">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-primary">
                  <UserRound className="w-4 h-4" /> Specialists to speak with
                </div>
                <div className="mt-5 space-y-3">
                  {advice.recommended_specialists.map((s, i) => (
                    <div key={i} className="rounded-lg bg-muted/60 px-4 py-3">
                      <div className="font-medium">{s.role}</div>
                      <div className="text-sm text-muted-foreground mt-0.5">{s.why}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Next steps */}
            {advice.next_steps?.length > 0 && (
              <div data-testid="next-steps-card" className="lg:col-span-5 bg-primary/5 border border-primary/20 rounded-2xl p-7">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-primary">
                  <CheckCircle2 className="w-4 h-4" /> Your next steps
                </div>
                <ol className="mt-5 space-y-3">
                  {advice.next_steps.map((n, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="w-6 h-6 flex-shrink-0 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-medium">{i + 1}</span>
                      <span className="text-sm text-foreground/90">{n}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Mindset */}
            {advice.mindset_tips?.length > 0 && (
              <div data-testid="mindset-card" className="lg:col-span-12 rounded-2xl overflow-hidden border border-border">
                <div className="grid md:grid-cols-5">
                  <div className="md:col-span-2 min-h-[220px]">
                    <img
                      src="https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?crop=entropy&cs=srgb&fm=jpg&q=85&w=800"
                      alt="A smiling doctor with a patient"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="md:col-span-3 p-7 bg-white">
                    <div className="text-xs uppercase tracking-[0.2em] text-primary">Mindset & wellbeing</div>
                    <h3 className="mt-3 font-light text-2xl tracking-tight">You are stronger than this moment.</h3>
                    <ul className="mt-5 space-y-3">
                      {advice.mindset_tips.map((t, i) => (
                        <li key={i} className="flex gap-3 text-sm">
                          <Sparkles className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {advice.disclaimer && (
              <p data-testid="disclaimer" className="lg:col-span-12 text-xs text-muted-foreground mt-2">
                {advice.disclaimer}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
