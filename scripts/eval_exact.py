import glob, os, sys, torch
sys.path.insert(0, "/app/backend")
from models import pinn_predictor as P
ORDER = ["glioma_tumor", "meningioma_tumor", "no_tumor", "pituitary_tumor"]
cm = torch.zeros(4, 4, dtype=torch.int)
for f in sorted(glob.glob("/app/scripts/mri_samples/*.jpg")):
    t = ORDER.index(os.path.basename(f).rsplit("_", 1)[0])
    r = P.predict(open(f, "rb").read())
    cm[t, P.TUMOR_CLASSES.index(r.tumor_type)] += 1
print(P.model_status()["load_error"], "acc", cm.diag().sum().item() / cm.sum().item()); print(cm)
r = P.predict(open("/app/scripts/mri_samples/pituitary_tumor_5.jpg", "rb").read())
print(r.tumor_type, r.confidence, "area%", r.tumor_area_pct, "heatmap kb", len(r.heatmap) // 1024)
