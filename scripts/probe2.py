import torch
from probe_pinn import Net, SD, load, labels, files
for size in [256, 320, 384]:
    X = load(size, "imnet")
    net = Net("A", "u_lap_res"); net.load_state_dict(SD); net.eval()
    with torch.no_grad(): p = net(X).argmax(1)
    cm = torch.zeros(4,4,dtype=torch.int)
    for t,q in zip(labels,p): cm[t,q]+=1
    print(size, (p==labels).float().mean().item()); print(cm)
