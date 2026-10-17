# Physics ideas

John-approved research ideas for the civilizations layer in [civilizations.md](civilizations.md). The first four are **SIGNATURE** features of the core civ layer. Items 5–15 are later layers. Formulas and source links are kept as given. None of this is in `civ_sim.py`.

The four shipped endings stay the names in that sketch. The transcend ending named under Kerr lensing is the shipped id `wonder`, The open orchard. These ideas do not add a fifth ending.

## SIGNATURE features of the core civ layer

These four belong with the core civ layer: the tribe stats, the utility tick, and the crowd that later becomes Mass AI. They are not a later band.

### 1. Kuramoto faith sync

```
dθ_i/dt = ω_i + (K/N) Σ sin(θ_j − θ_i)
```

Order parameter:

```
r e^{iψ} = (1/N) Σ e^{iθ_j}
```

Critical coupling:

```
K_c = 2/(π g(0))
```

Miracles raise K, prophets narrow the spread of ω, and r is a visible Unity stat. Falling below K_c causes a schism into sects. Mass AI processor, one float per agent.

Source: Strogatz 2000, https://doi.org/10.1016/S0167-2789(00)00094-4

### 2. Lenia 'Breath of Life' (Days 3-5)

```
A' = clip(A + Δt·G(K*A))
G = 2exp(-(u-μ)²/2σ²) - 1
```

Voice tunes μ, σ, and the kernel. Named species get promoted to 3D fauna. 512² compute shader with FFT.

Source: https://arxiv.org/abs/1812.05433

### 3. Landauer miracle cost

```
cost = k_B·T_world·ln2·ΔI_bits
```

Erasing possibilities costs Power. Cold places are cheap and hot battlefields costly. The waste heat goes into weather.

Source: https://doi.org/10.1038/nature10872

### 4. Ising societies

```
H = −J Σ s_i s_j − h Σ s_i
```

Metropolis flips with `P = min(1, e^{−ΔE/T})`.

h = God's influence, J = cohesion, T = unrest. Near T_c one miracle flips a civilization. Deffuant bounded confidence forms sects.

Source: https://arxiv.org/abs/0710.3256

## Later layers

These stay outside the core civ tick. They land with the later bands already named in the civilizations sketch, or after them.

### 5. Kerr black-hole lensing

A baked LUT post-process for the pre-creation void, the multiverse map, and the transcend ending.

Source: https://arxiv.org/abs/1502.03808

### 6. Quantum-walk prophecy spread

Prophecy spreads on the settlement graph, tied to the observer system.

Source: https://arxiv.org/abs/quant-ph/0303081

### 7. Active inference for NPC minds

A miracle is surprise, leading to conversion or hostility and the crucifixion path.

Source: https://doi.org/10.1038/nrn2787

### 8. Anthropic fine-tuning

31 constants per multiverse seed.

Source: https://arxiv.org/abs/astro-ph/0511774

### 9. PB-MPM sand, mud, and clay sculpting

Sand, mud, and clay sculpting, and forming Adam from clay.

Source: https://www.ea.com/seed/news/siggraph2024-pbmpm

### 10. Bubble-universe collisions

Source: https://arxiv.org/abs/0908.4105

### 11. Gray-Scott living patterns

Source: https://arxiv.org/abs/patt-sol/9304003

### 12. Network percolation

The spread of faith or plague, and smiting hubs.

Source: https://arxiv.org/abs/cond-mat/0007300

### 13. Page-Wootters 'God outside time' scrub mode

Source: https://arxiv.org/abs/1310.4691

### 14. Schrödinger's smoke as divine breath

Source: https://doi.org/10.1145/2897824.2925868

### 15. IIT soul meter (contested theory)

Source: https://arxiv.org/abs/2212.14787
