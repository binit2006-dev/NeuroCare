import { useRef, useState } from "react";
import { Upload, MapPin, X, FileImage } from "lucide-react";
import { toast } from "sonner";
import { predictMRI } from "@/lib/api";

export default function Uploader({ onComplete, setLoading }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [location, setLocation] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const pick = (f) => {
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      toast.error("Please choose a JPG or PNG MRI image.");
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    pick(e.dataTransfer.files?.[0]);
  };

  const clear = () => { setFile(null); setPreview(null); };

  const submit = async () => {
    if (!file) { toast.error("Add an MRI image first."); return; }
    try {
      setLoading(true);
      const scan = await predictMRI(file, location);
      onComplete({ ...scan, preview });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="scan" data-testid="uploader-section" className="py-20">
      <div className="max-w-5xl mx-auto px-6 lg:px-10">
        <div className="max-w-xl">
          <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium">Step 1 of 2</p>
          <h2 className="mt-3 font-light text-2xl sm:text-3xl lg:text-4xl tracking-tight">
            Upload your MRI scan
          </h2>
          <p className="mt-3 text-muted-foreground">
            Drag a JPG or PNG of your brain MRI below. Your file is used only to run the analysis.
          </p>
        </div>

        <div className="mt-10 grid lg:grid-cols-5 gap-8">
          <div className="lg:col-span-3">
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              data-testid="dropzone"
              className={`relative rounded-2xl border-2 border-dashed p-10 cursor-pointer min-h-[280px] flex flex-col items-center justify-center text-center ${
                dragOver ? "border-primary bg-primary/5" : "border-primary/40 bg-white hover:bg-primary/5"
              }`}
            >
              <input
                ref={inputRef}
                data-testid="file-input"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => pick(e.target.files?.[0])}
              />
              {preview ? (
                <div className="relative">
                  <img src={preview} alt="MRI preview" className="max-h-56 rounded-lg object-contain" />
                  <button
                    data-testid="clear-file-button"
                    onClick={(e) => { e.stopPropagation(); clear(); }}
                    className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-white border border-border flex items-center justify-center shadow-sm hover:bg-muted"
                    aria-label="Remove"
                  >
                    <X className="w-4 h-4" />
                  </button>
                  <p className="mt-3 text-sm text-muted-foreground flex items-center gap-1.5 justify-center">
                    <FileImage className="w-4 h-4" />
                    {file?.name}
                  </p>
                </div>
              ) : (
                <>
                  <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                    <Upload className="w-6 h-6 text-primary" strokeWidth={1.75} />
                  </div>
                  <p className="font-medium">Drop your MRI image here</p>
                  <p className="text-sm text-muted-foreground mt-1">or click to browse · JPG, PNG</p>
                </>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 flex flex-col gap-5">
            <div>
              <label className="text-sm font-medium flex items-center gap-2">
                <MapPin className="w-4 h-4 text-primary" /> Your city or pincode
              </label>
              <input
                data-testid="location-input"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Mumbai, 400001"
                className="mt-2 w-full px-4 py-3 rounded-md bg-white border border-border focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
              />
              <p className="text-xs text-muted-foreground mt-2">
                Helps us recommend hospitals and emergency numbers close to you.
              </p>
            </div>

            <button
              data-testid="analyze-button"
              onClick={submit}
              disabled={!file}
              className="w-full py-3.5 rounded-full bg-primary text-primary-foreground font-medium hover:bg-[#3a6347] hover:-translate-y-[1px] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            >
              Analyse scan
            </button>

            <div className="rounded-lg bg-secondary/20 border border-secondary/50 p-4 text-sm text-foreground/80">
              <strong className="font-medium">You&apos;re in good hands.</strong> This tool is educational.
              Whatever the result, we&apos;ll walk you through calm, concrete next steps.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
