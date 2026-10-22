export default function BreathingLoader({ label = "Analysing your scan…" }) {
  return (
    <section data-testid="breathing-loader" className="py-28">
      <div className="max-w-xl mx-auto px-6 text-center">
        <div className="relative mx-auto w-48 h-48">
          <div className="absolute inset-0 rounded-full bg-primary/10 breathe" />
          <div className="absolute inset-6 rounded-full bg-primary/20 breathe" style={{ animationDelay: "-1.1s" }} />
          <div className="absolute inset-12 rounded-full bg-primary/40 breathe" style={{ animationDelay: "-2.2s" }} />
          <div className="absolute inset-16 rounded-full bg-primary" />
        </div>
        <h3 className="mt-10 font-light text-2xl tracking-tight">{label}</h3>
        <p className="mt-3 text-muted-foreground">Take a slow breath. This will only take a moment.</p>
      </div>
    </section>
  );
}
