import torch, itertools, torch.nn.functional as F
from probe_pinn import Net, SD, load, labels
X = load(256, "imnet")
net = Net("A", "u_lap_res"); net.load_state_dict(SD); net.eval()
feats = {}
def hook(m, i, o): feats["e4"] = o
net.block4.register_forward_hook(hook)
with torch.no_grad(): net(X)
g = F.adaptive_avg_pool2d(feats["e4"], 1).flatten(1)
print("img feat mean", g.mean().item(), "max", g.max().item())
W = SD["classifier.1.weight"][:, 256:]
print("phys weight cols norm", W.norm(dim=0))
best = []
vals = [-2, -1, -0.5, 0, 0.25, 0.5, 1, 2, 5]
for c in itertools.product(vals, repeat=3):
    p = torch.tensor(c).float().expand(len(X), 3)
    with torch.no_grad(): pr = net.classifier(torch.cat([g, p], 1)).argmax(1)
    best.append(((pr == labels).float().mean().item(), c, torch.bincount(pr, minlength=4).tolist()))
best.sort(key=lambda t: -t[0])
for b in best[:8]: print(b)
