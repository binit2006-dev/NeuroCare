import { useRef, useState } from "react";
import Hero from "@/components/Hero";
import Uploader from "@/components/Uploader";
import BreathingLoader from "@/components/BreathingLoader";
import Results from "@/components/Results";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [scan, setScan] = useState(null);
  const uploaderRef = useRef(null);

  const scrollToUploader = () => {
    const el = document.getElementById("scan");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  const reset = () => {
    setScan(null);
    setTimeout(scrollToUploader, 50);
  };

  return (
    <div ref={uploaderRef}>
      {!scan && <Hero onCta={scrollToUploader} />}
      {!scan && !loading && (
        <Uploader onComplete={setScan} setLoading={setLoading} />
      )}
      {loading && <BreathingLoader />}
      {scan && !loading && <Results scan={scan} onReset={reset} />}
    </div>
  );
}
