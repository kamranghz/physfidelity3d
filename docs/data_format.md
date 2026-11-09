# Data format

## Evaluation records

```
data/records/<dataset>/<scene_id>/<method>/
  nps.json          Non-Penetration Score and all penetration terms
  sps.json          Scene Plausibility Score after the PyBullet rollout
  mesh_stats.json   per-object mesh statistics
```

`dataset` is `ycbv`, `tless` or `picasso`; `method` is `dust3r`, `mast3r`, `vggt`, `vggt_omega` or `vgg_t3`.
YCB-V and T-LESS scenes use their BOP scene ids; Picasso scenes use their scene names.
The files are the outputs of the benchmark run, unchanged. Their SHA-256 hashes are listed in
`data/checksums.sha256`, and JSON schemas are in `data/schema/`.

### nps.json

| Field | Meaning |
|:--|:--|
| `nps_scene_mm` | scene NPS in mm (mean of per-object NPS) |
| `per_object_nps_mm` | NPS per object id |
| `object_order` | object ids in the order used by the matrices |
| `pen_matrix_mm` | pairwise penetration, capped at 10 mm (symmetric) |
| `pen_matrix_raw_mm` | pairwise penetration without the cap |
| `cap_hit_matrix` | `true` where the raw value reaches the cap |
| `per_object_env_pen_mm`, `per_object_env_pen_raw_mm` | object-to-support-plane penetration, capped and raw |
| `n_objects`, `n_cap_hits`, `cap_hit_fraction`, `pen_cap_m` | counts and the cap (0.01 m) |
| `formula`, `indicator`, `sdf_tool`, `free_space_skipped` | provenance; equation numbers refer to the Picasso paper (arXiv:2602.08058) |

### sps.json

| Field | Meaning |
|:--|:--|
| `sps_scene` | scene SPS in J |
| `per_object_ke` | residual kinetic energy terms per object |
| `n_steps`, `timestep_s` | rollout of 20 steps at 1/240 s |
| `canonical_mass_kg`, `canonical_inertia` | 1 kg and identity inertia for every object |
| `ke_cap_per_component_kgm2s2` | 10 J cap per energy term |
| `blow_up` | numerical blow-up flag (false for all 210 records) |

### mesh_stats.json

Per object id: `watertight`, `vertex_count`, `face_count`, `volume_m3`. Watertight meshes are decomposed
with CoACD for SPS; the others use a single convex hull (Table 7).

## Recorded results

`data/recorded/` holds results that need reconstructions or ground truth, which are not redistributed.

| File | Paper |
|:--|:--|
| `geometry_metrics.csv` | Table 3: depth RMSE on the shared GT-valid pixels and surface-sampled CAD Chamfer, mm |
| `geometry_correlations.csv` | Section 4.2: Spearman rho with scene-cluster bootstrap 95% CIs |
| `gt_aligned_pooled.csv` | Table 4, Fig. 7: means, CIs and ranks under the original and GT-aligned protocols |
| `gt_aligned_paired.csv` | Table 5, Fig. 8: VGGT-family aligned − native paired differences |
| `scale_perturbation.csv` | Fig. 9: pooled means under global scale perturbation, three scenes |
