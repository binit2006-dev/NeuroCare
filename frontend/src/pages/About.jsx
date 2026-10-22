import { useEffect, useState } from "react";
import { fetchModelStatus } from "@/lib/api";
import { Atom, Database, Shield, Sparkles, FolderOpen } from "lucide-react";

export default function About() {
  const [status, setStatus] = useState(null);
  useEffect(() => { fetchModelStatus().then(setStatus).catch(() => {}); }, []);

  return (
    <div className="relative">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-32 right-10 w-[520px] h-[520px] rounded-full bg-accent/25 blur-3xl drift" />
      </div>

      <section className="max-w-5xl mx-auto px-6 lg:px-10 pt-20 pb-10">
        <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium">About the technology</p>
        <h1 className="mt-4 font-light text-4xl sm:text-5xl lg:text-6xl tracking-tight">
          Physics-Informed Neural Networks, <span className="text-primary">simply explained.</span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-2xl leading-relaxed">
          A PINN is a neural network that doesn&apos;t only learn from data — it also respects the laws of
          physics that describe how biological tissue, imaging contrast and MRI signals actually behave.
          The result: fewer false predictions, more trustworthy outputs.
        </p>
      </section>

      <section className="max-w-6xl mx-auto px-6 lg:px-10 grid md:grid-cols-3 gap-5 pb-12">
        {[
          { icon: Atom, title: "Physics-aware", text: "Loss function includes PDE constraints alongside classification loss." },
          { icon: Database, title: "4-class output", text: "no_tumor · glioma · meningioma · pituitary with calibrated confidence." },
          { icon: Shield, title: "Private by design", text: "No account needed. Scans are only used for this prediction." },
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
                <FolderOpen className="w-4 h-4" /> Where to plug your model
              </div>
              <h2 className="mt-3 font-light text-2xl sm:text-3xl tracking-tight">
                Drop your trained model into one folder.
              </h2>
              <ol className="mt-5 space-y-3 text-sm">
                <li className="flex gap-3">
                  <span className="w-6 h-6 flex-shrink-0 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-medium">1</span>
                  <div>Open the project folder <code className="px-1.5 py-0.5 rounded bg-muted text-xs">/app/backend/models/</code>.</div>
                </li>
                <li className="flex gap-3">
                  <span className="w-6 h-6 flex-shrink-0 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-medium">2</span>
                  <div>Drop your file. Supported names: <code className="px-1.5 py-0.5 rounded bg-muted text-xs">pinn_model.pth</code>, <code className="px-1.5 py-0.5 rounded bg-muted text-xs">.pt</code>, <code className="px-1.5 py-0.5 rounded bg-muted text-xs">.h5</code>, <code className="px-1.5 py-0.5 rounded bg-muted text-xs">.onnx</code>.</div>
                </li>
                <li className="flex gap-3">
                  <span className="w-6 h-6 flex-shrink-0 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center font-medium">3</span>
                  <div>Open <code className="px-1.5 py-0.5 rounded bg-muted text-xs">pinn_predictor.py</code> and uncomment the loader + inference block for your framework.</div>
                </li>
              </ol>

              <div className="mt-6 rounded-lg bg-muted/60 p-4 text-sm">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <span className="font-medium">Current status</span>
                </div>
                {status ? (
                  <div data-testid="model-status" className="mt-2 grid grid-cols-2 gap-y-1 text-xs">
                    <span className="text-muted-foreground">Model loaded</span>
                    <span>{status.model_loaded ? "Yes" : "No (demo mode)"}</span>
                    <span className="text-muted-foreground">Model file</span>
                    <span>{status.model_file || "—"}</span>
                    <span className="text-muted-foreground">Classes</span>
                    <span>{status.classes?.join(" · ")}</span>
                  </div>
                ) : (
                  <div className="mt-2 text-xs text-muted-foreground">Checking…</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
