# Seed-based multiverse

`unreal/multiverse` generates a universe from one 64-bit seed, gives that universe its own physics constants, and records God's major choices as a branching tree. The package is pure Python plus the JSON catalogs in `unreal/Data`. It does not import Unreal, does not ship a model, and does not open a socket.

The Day 1 level script still builds one garden. This layer is the record of which universe that garden belongs to, and of the forks a lasting choice opens.

## A universe is a 64-bit seed

A seed is an integer in `0 .. 2**64 - 1`. `Multiverse(1)` and `Multiverse("0x1")` are the same universe. Strings are hexadecimal, with an optional `0x` prefix. The save file writes every seed as 16 lowercase hex digits, because a JSON number is not exact past 2**53.

`Multiverse.originate(source)` draws one root seed from a `SeedSource` and then forgets the source. Later branches do not draw again. They mix the parent seed with the choice id.

## Physics constants

Each universe has the 31 bands in `Data/physics_constants.json`, in that file's order. The count follows the anthropic constant set discussed by Rees (astro-ph/0511774). The numbers here are playable garden bands: gravity you can walk in, a day a person can live, water that still has a liquid window. Nominal is the reference garden. The generator draws uniformly inside each band. It does not solve a habitable-zone equation, so a bright star can share a seed with a near orbit. Every individual number still lands inside its own band.

`water_freezing_c` tops out at 15 C and `water_boiling_c` starts at 70 C, so freezing stays below boiling for every seed.

### Derivation

The derivation tag is `elyon.multiverse.v1`.

The seed is the SplitMix64 state (Vigna). For each constant, in file order:

1. Step SplitMix64. Keep the output word and the next state.
2. Keep the top 53 bits: `top = word >> 11`. Those integers are exact in IEEE-754 binary64.
3. `t = (top + 0.5) / 2**53`, so `t` lies in `(0, 1)`.
4. `raw = min + t * (max - min)`.
5. Quantize with Python `round(raw, places)` (half to even), then clamp back into `[min, max]`. A result of `-0.0` is stored as `0.0`.

The same seed always produces the same constants. One bit of seed change is enough to change the set.

SplitMix64 from state `0` yields `e220a8397b1dcdaf` on the first step.

Worked universe, seed `1` (`0000000000000001`):

| Constant | Value |
| --- | --- |
| `gravity` | 15.031 m/s^2 |
| `light_speed` | 373734527 m/s |
| `planck_ratio` | 1.471003 |

### Bands

| id | name | unit | nominal | min | max | places |
| --- | --- | --- | --- | --- | --- | --- |
| `gravity` | Surface gravity | m/s^2 | 9.81 | 2 | 25 | 3 |
| `light_speed` | Speed of light | m/s | 299792458 | 150000000 | 450000000 | 0 |
| `planck_ratio` | Planck constant ratio | ratio | 1 | 0.5 | 1.5 | 6 |
| `fine_structure` | Fine-structure constant | 1 | 0.007297 | 0.005 | 0.012 | 6 |
| `electron_proton_ratio` | Electron to proton mass | ratio | 0.000545 | 0.0002 | 0.002 | 6 |
| `strong_coupling` | Strong coupling | 1 | 0.118 | 0.08 | 0.2 | 4 |
| `weak_coupling` | Weak scale ratio | ratio | 1 | 0.5 | 2 | 4 |
| `cosmological_ratio` | Cosmological constant ratio | ratio | 1 | 0.1 | 10 | 4 |
| `baryon_fraction` | Baryon fraction | fraction | 0.05 | 0.01 | 0.2 | 4 |
| `dark_matter_fraction` | Dark matter fraction | fraction | 0.27 | 0.05 | 0.6 | 4 |
| `dark_energy_fraction` | Dark energy fraction | fraction | 0.68 | 0.2 | 0.9 | 4 |
| `expansion_rate` | Valley expansion | 1/Gyr | 0.07 | 0.01 | 0.2 | 4 |
| `curvature` | Spatial curvature | 1 | 0 | -0.2 | 0.2 | 4 |
| `day_length_hours` | Day length | h | 24 | 8 | 48 | 2 |
| `year_length_days` | Year length | d | 365 | 80 | 800 | 1 |
| `axial_tilt_deg` | Axial tilt | deg | 23.4 | 0 | 45 | 2 |
| `mean_temperature_c` | Mean temperature | C | 15 | -5 | 40 | 2 |
| `atmosphere_pressure_atm` | Surface pressure | atm | 1 | 0.4 | 3 | 3 |
| `oxygen_fraction` | Oxygen fraction | fraction | 0.21 | 0.1 | 0.35 | 3 |
| `water_freezing_c` | Water freezes | C | 0 | -5 | 15 | 2 |
| `water_boiling_c` | Water boils | C | 100 | 70 | 130 | 2 |
| `world_radius_km` | World radius | km | 6371 | 1000 | 20000 | 0 |
| `world_mass_earths` | World mass | Earth masses | 1 | 0.1 | 5 | 3 |
| `star_luminosity_suns` | Star luminosity | solar luminosities | 1 | 0.3 | 3 | 3 |
| `orbital_radius_au` | Orbital radius | AU | 1 | 0.4 | 2.5 | 3 |
| `magnetic_field_gauss` | Magnetic field | G | 0.5 | 0.05 | 5 | 3 |
| `air_density_kg_m3` | Air density | kg/m^3 | 1.2 | 0.3 | 4 | 3 |
| `sound_speed_m_s` | Sound speed | m/s | 343 | 150 | 700 | 1 |
| `time_flow` | Mortal clock per god clock | ratio | 1 | 0.25 | 4 | 3 |
| `chemistry_rate` | Chemistry and growth | ratio | 1 | 0.2 | 3 | 3 |
| `mutation_rate` | Lineage drift | ratio | 1 | 0.1 | 5 | 3 |

Changing a band, its order, or its decimal places changes `physics_fingerprint()` and invalidates format-1 saves. Adding a major choice does not.

## Major choices

A major choice is an edge. The catalog is `Data/major_choices.json`. These are the lasting choices the garden already understands: light, the four endings, the valley, a pact, a raid, the sky, and the present. The summary text in that file is the meaning of the edge. Branching stores the edge and derives the child. It does not resimulate the year.

| id | label | group |
| --- | --- | --- |
| `let_there_be_light` | Let there be light | light |
| `leave_darkness` | Leave the dark | light |
| `ending_harmony` | The garden kept | ending |
| `ending_exile` | East of the garden | ending |
| `ending_wonder` | The open orchard | ending |
| `ending_order` | The closed question | ending |
| `keep_in_valley` | Keep them in the valley | valley |
| `send_out` | Send them out | valley |
| `bless_pact` | Bless a pact | covenant |
| `withhold_pact` | Withhold the pact | covenant |
| `stop_raid` | Stop the raid | covenant |
| `allow_raid` | Let the raid go | covenant |
| `send_rain` | Send rain | sky |
| `send_drought` | Send a drought | sky |
| `send_flood` | Send a flood | sky |
| `bless_present` | Bless the present | present |
| `keep_commons` | Keep a commons | present |

### Child seeds

```
message = ascii(derivation) || NUL || parent_seed_be64 || NUL || utf8(choice_id)
child_seed = first 8 bytes of SHA-256(message), big-endian
```

`choice_id` is the catalog id, matched exactly. An unknown id raises `UnknownChoice` and adds no node. The same choice on the same parent returns the existing child. A different choice is a sibling. A further choice mixes the child seed, not the root, so `root / send_rain / ending_harmony` and `root / ending_harmony` are different universes.

The child seed is a new SplitMix64 state. Its constants are derived from that seed alone, not as a delta from the parent.

Worked edge: parent seed `1`, choice `let_there_be_light`, child seed `c82251958a7e1d07`. The child id is `root/let_there_be_light`.

## The tree

- The root id is `root`. It has no parent and no choice.
- A child id is `{parent_id}/{choice_id}`.
- `branch(choice_id)` forks from the focus. Pass `parent_id` to fork from somewhere else.
- `follow` defaults to true and moves the focus onto the child. `follow=False` leaves the focus where it is.
- `lineage` walks root first. `choice_path` is the choice ids along that walk.
- Universe objects are immutable snapshots. After a branch, call `get` or `root` again to see the new child list.

Depth is the number of slashes in the id. A tree holds at most 4096 universes.

## Save and load

`save(path)` writes UTF-8 JSON, keys sorted, one trailing newline, LF line endings. `load(path)` and `from_dict` rebuild the tree.

Top-level keys: `format`, `derivation`, `physics`, `focus_id`, `nodes`.

- `format` is `1`.
- `derivation` is `elyon.multiverse.v1`.
- `physics` is the 16-hex catalog fingerprint.
- Each node stores `id`, `seed`, `parent_id`, `choice_id`, `depth`, `child_ids`, and `constants`.
- Constants are decimal strings with the catalog's `places`, not JSON numbers.
- On load, every child seed is mixed again and every constant string is checked against a fresh derivation. A mismatch raises `SaveError`.

Node order in the file is preserved. A parent may be listed after its child. The links are checked either way.

## Seed sources

`SeedSource.next_seed` returns one unsigned 64-bit integer.

`LocalRngSource` is the default.

- `LocalRngSource(seed)` replays SplitMix64. The same constructor seed yields the same stream of root seeds. That stream is not the constructor seed itself: the first draw is the first SplitMix64 output.
- `LocalRngSource()` with no seed reads 8 bytes from `os.urandom` on each call. That is this machine's local generator.

`QuantumSeedSource` is the stub for an external quantum randomness source.

- `QuantumSeedSource()` has no provider. `next_seed` raises `QuantumSourceUnavailable`.
- Pass a callable that returns exactly 8 bytes. A `bytearray` of length 8 is accepted. The seed is those bytes, big-endian.
- A string or a URL is rejected. The class does not contact a network service, and the package does not import a network stack. A future adapter can wrap a local device or an offline buffer behind the same callable.

```python
from multiverse import LocalRngSource, Multiverse, QuantumSeedSource

world = Multiverse(1)
dawn = world.branch("let_there_be_light")
rain = world.branch("send_rain")
world.save("multiverse.json")
again = Multiverse.load("multiverse.json")

replay = LocalRngSource(seed=1)
fresh_root = Multiverse.originate(replay)

hardware = QuantumSeedSource(provider=read_eight_local_bytes)
```

Run that snippet with `PYTHONPATH` set to the `unreal` directory. `read_eight_local_bytes` is the caller's local provider. The package does not define one.

## Tests

From the repo root:

```bash
python3 -m unittest discover -s unreal/tests -v
```

`unreal/tests/test_multiverse.py` covers the SplitMix64 vector, the worked seed, the bands, every major choice, idempotent branching, grandchild seeds, save/load, tampered saves, both seed sources, and a scan that the package does not import a network client.
