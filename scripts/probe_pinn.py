import glob, itertools, os
import torch, torch.nn as nn, torch.nn.functional as F
from PIL import Image
import numpy as np

SD = torch.load("/app/backend/models/pinn_model.pth", map_location="cpu")
ORDER = ["glioma_tumor", "meningioma_tumor", "no_tumor", "pituitary_tumor"]


def block(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(True),
                         nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(True))


class Net(nn.Module):
    def __init__(s, dec, phys):
        super().__init__()
        s.dec, s.phys = dec, phys
        s.log_D = nn.Parameter(torch.tensor(0.)); s.log_rho = nn.Parameter(torch.tensor(0.))
        s.register_buffer("lap_kernel", torch.zeros(1, 1, 3, 3))
        s.block1, s.block2, s.block3, s.block4 = block(3, 32), block(32, 64), block(64, 128), block(128, 256)
        s.up1 = nn.Conv2d(256, 64, 3, padding=1); s.up2 = nn.Conv2d(192, 32, 3, padding=1)
        s.up3 = nn.Conv2d(96, 32, 3, padding=1); s.out = nn.Conv2d(32, 1, 1)
        s.classifier = nn.Sequential(nn.Dropout(), nn.Linear(259, 128), nn.ReLU(), nn.Dropout(), nn.Linear(128, 4))

    def forward(s, x):
        P = lambda t: F.max_pool2d(t, 2)
        e1 = s.block1(x); e2 = s.block2(P(e1)); e3 = s.block3(P(e2)); e4 = s.block4(P(e3))
        up = lambda t, r: F.interpolate(t, size=r.shape[-2:], mode="bilinear", align_corners=False)
        if s.dec == "A":
            d = F.relu(s.up1(up(e4, e3))); d = torch.cat([d, e3], 1)
            d = F.relu(s.up2(up(d, e2))); d = torch.cat([d, e2], 1)
            d = F.relu(s.up3(up(d, e1)))
        elif s.dec == "B":
            d = up(F.relu(s.up1(e4)), e3); d = torch.cat([d, e3], 1)
            d = up(F.relu(s.up2(d)), e2); d = torch.cat([d, e2], 1)
            d = up(F.relu(s.up3(d)), e1)
        else:
            d = up(F.relu(s.up1(e4)), e3); d = torch.cat([d, e3], 1)
            d = up(F.relu(s.up2(d)), e2); d = torch.cat([d, e2], 1)
            d = up(F.relu(s.up3(d)), x)
        u = torch.sigmoid(s.out(d))
        lap = F.conv2d(u, s.lap_kernel, padding=1)
        D, rho = s.log_D.exp(), s.log_rho.exp()
        react = rho * u * (1 - u)
        res = D * lap + react
        B = x.shape[0]
        m = lambda t: t.view(B, -1).mean(1)
        p = {
            "u_lap_res": [m(u), m(lap.abs()), m(res.abs())],
            "D_rho_res": [D.expand(B), rho.expand(B), m(res.abs())],
            "u_std_res": [m(u), u.view(B, -1).std(1), m(res.abs())],
            "u_lap_react": [m(u), m(lap.abs()), m(react)],
            "res2_u_max": [m(res ** 2), m(u), u.view(B, -1).amax(1)],
            "u_res_react": [m(u), m(res.abs()), m(react)],
            "u_res2_react": [m(u), m(res ** 2), m(react)],
            "u_lap2_react": [m(u), m(lap ** 2), m(react)],
            "zeros": [torch.zeros(B)] * 3,
        }[s.phys]
        feat = torch.cat([F.adaptive_avg_pool2d(e4, 1).flatten(1), torch.stack(p, 1)], 1)
        return s.classifier(feat)


files = sorted(glob.glob("/app/scripts/mri_samples/*.jpg"))
labels = torch.tensor([ORDER.index(os.path.basename(f).rsplit("_", 1)[0]) for f in files])
NORMS = {"none": ([0, 0, 0], [1, 1, 1]), "imnet": ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]), "half": ([0.5] * 3, [0.5] * 3)}


def load(size, norm):
    mu, sd = NORMS[norm]
    xs = []
    for f in files:
        a = np.asarray(Image.open(f).convert("RGB").resize((size, size), Image.BILINEAR), dtype=np.float32) / 255.
        a = (a - mu) / sd
        xs.append(torch.tensor(a).permute(2, 0, 1).float())
    return torch.stack(xs)


if __name__ == "__main__":
    PHYS = ["u_lap_res", "D_rho_res", "u_std_res", "u_lap_react", "res2_u_max", "u_res_react", "u_res2_react", "u_lap2_react", "zeros"]
    results = []
    for size, norm in itertools.product([128, 224, 256], NORMS):
    X = load(size, norm)
    for dec, phys in itertools.product("ABC", PHYS):
        net = Net(dec, phys); net.load_state_dict(SD); net.eval()
        with torch.no_grad():
            pr = net(X).softmax(1)
        acc = (pr.argmax(1) == labels).float().mean().item()
        results.append((acc, pr.max(1).values.mean().item(), size, norm, dec, phys))
    results.sort(reverse=True)
    for r in results[:15]:
    print("acc=%.2f conf=%.2f size=%d norm=%s dec=%s phys=%s" % r)
    print("n images", len(files))
