# Research guide: from videos to explorable 3D scenes

Primary papers and official repositories checked on **2026-09-14**. This guide explains the relationship between published work and WolfWorld's current implementation. It is not a benchmark of those methods on WolfWorld captures.

## Three different problems

**Geometric reconstruction** estimates cameras and scene structure from observations. More overlapping views can constrain the result, but missing coverage, texture ambiguity and inconsistent motion remain difficult.

**Novel-view rendering** synthesizes images from new camera positions using a scene representation. A convincing render is not proof that measurements, surfaces or collisions are correct.

**World generation** invents additional content from learned priors. Generating an unseen wall can help create a complete-looking environment, but that wall is not an observation of the original room. WolfWorld currently calls reconstruction, not the generative pipeline.

These distinctions explain why a Gaussian viewer does not automatically provide a physics simulator, a metrically accurate building model, or a reliable reconstruction of footage with no overlap.

## Annotated reading list

### 1. HY-World 2.0 / WorldMirror 2.0 — current adapter

**Team HY-World et al., 2026.** [Paper](https://arxiv.org/abs/2604.14268) · [Code](https://github.com/Tencent-Hunyuan/HY-World-2.0) · [API/output documentation](https://github.com/Tencent-Hunyuan/HY-World-2.0/blob/main/DOCUMENTATION.md)

HY-World combines reconstruction and generation components. WorldMirror is its multi-view reconstruction component, with camera, depth, point and Gaussian outputs. WolfWorld's worker extracts a shared frame set and invokes that component. It does not integrate HY-Pano, WorldStereo, WorldNav or WorldLens.

The current worker targets source revision `df9988efb87bfc0f4947eb3889411cf957478b06`. A later upstream API or weight change may require adapter work; a compatible health check does not verify output quality. GPU acceptance remains pending.

**Read for:** model I/O, priors, reconstruction versus generation, and the upstream CLI contract. **Evaluate next:** single-room reconstruction, cross-video consistency, peak memory and failure recovery.

### 2. 3D Gaussian Splatting — representation foundation

**Kerbl, Kopanas, Leimkühler and Drettakis, 2023.** [Paper](https://arxiv.org/abs/2308.04079) · [Project](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) · [Reference code](https://github.com/graphdeco-inria/gaussian-splatting)

The work represents appearance with spatial Gaussians and optimizes their parameters for novel-view rendering. A Gaussian has more than a position: scale, orientation, opacity and appearance affect the image. This is why a generic XYZ/RGB point cloud cannot simply be renamed and loaded as a trained Gaussian scene.

WolfWorld uses the representation and a separate browser renderer. It does not reproduce the paper's evaluation, claim the paper's frame rate, or run its original training system.

**Read for:** splat parameterization, optimization and rendering. **Evaluate next:** fidelity away from training views, floaters, memory use and render speed on the actual device.

### 3. Depth Anything 3 — candidate geometry backend

**Lin et al., 2025.** [Paper](https://arxiv.org/abs/2511.10647) · [Code and model table](https://github.com/ByteDance-Seed/Depth-Anything-3) · [Streaming pipeline](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/main/da3_streaming/README.md)

DA3 predicts spatial geometry from one or multiple visual inputs, with or without supplied poses. The repository also provides a streaming path for longer sequences. That makes it a useful candidate for experiments beyond a bounded room capture.

WolfWorld does not contain a DA3 adapter. Streaming geometry output should not be assumed to be a drop-in, optimized Gaussian scene; verify each pipeline's export contract and add registration/training where needed. Code and checkpoint licenses differ across model variants, so record the exact checkpoint.

**Read for:** geometry prediction and sequence processing. **Evaluate next:** long-sequence drift, chunk alignment, export conversion and like-for-like input budgets.

### 4. VGGT — candidate camera/geometry baseline

**Wang et al., CVPR 2025.** [Paper](https://arxiv.org/abs/2503.11651) · [Code](https://github.com/facebookresearch/vggt) · [Current upstream license](https://github.com/facebookresearch/vggt/blob/main/LICENSE.txt)

VGGT jointly predicts geometric attributes such as camera parameters, depth and point maps from multiple images. Its repository includes paths toward COLMAP-format reconstruction, making it useful for comparing learned geometry with downstream geometric optimization.

A WolfWorld integration would require an adapter, output conversion, a defined registration strategy, and evaluation. It is currently a research reference, not a selectable backend. Use the current VGGT license and relevant checkpoint terms rather than an old blanket description of the project.

**Read for:** joint geometry estimation and export interfaces. **Evaluate next:** camera coverage, repeated structure and consistency with an optimized baseline.

### 5. gsplat — candidate refinement infrastructure

**Ye et al., 2024.** [Paper](https://arxiv.org/abs/2409.06765) · [Code](https://github.com/nerfstudio-project/gsplat) · [Documentation](https://docs.gsplat.studio/)

Gsplat provides Gaussian rasterization and optimization infrastructure. It can support a refinement stage when images, cameras and a suitable initialization are available. Installing it is not itself equivalent to training or improving a scene.

The worker's upstream environment includes a pinned gsplat dependency. WolfWorld has no separate post-reconstruction photometric optimization stage. Adding one requires explicit camera/image alignment, training configuration, checkpointing and evidence that the added cost improves the result.

**Read for:** differentiable rendering and implementation details. **Evaluate next:** quality versus optimization time, retained geometry, artifact count and export compatibility.

### 6. DUSt3R — pointmap background

**Wang et al., CVPR 2024.** [Paper](https://arxiv.org/abs/2312.14132) · [Code](https://github.com/naver/dust3r)

DUSt3R learns pointmaps for image pairs and supports recovering geometry without starting from a traditional calibrated reconstruction. Its alignment machinery is useful background for understanding how predictions across observations can be put into a common coordinate system.

WolfWorld does not depend on DUSt3R. The relevance is conceptual and experimental: predicted geometry still needs a consistent frame of reference and evidence of reliability.

### 7. COLMAP — geometric baseline and capture guidance

**Schönberger and Frahm, CVPR 2016, Structure-from-Motion Revisited.** [Official project and citation](https://colmap.github.io/) · [Code](https://github.com/colmap/colmap) · [Capture/tutorial guide](https://colmap.github.io/tutorial.html)

COLMAP provides structure-from-motion and multi-view stereo. It is a useful baseline for recovering cameras and checking geometric consistency, and its capture guidance explains why overlap and camera translation matter.

WolfWorld currently does not run COLMAP, bundle adjustment, loop closure or a calibrated scale-recovery stage. Adding these is an engineering project, not a matter of concatenating scene files.

### 8. NeRF — radiance-field background

**Mildenhall et al., ECCV 2020.** [Paper](https://arxiv.org/abs/2003.08934) · [Project](https://www.matthewtancik.com/nerf) · [Code](https://github.com/bmild/nerf)

NeRF represents a scene with a neural radiance field for view synthesis. It is useful background for the distinction between reconstructing appearance, rendering novel views and recovering explicit surfaces.

WolfWorld has no NeRF training or conversion path. The paper is included to help readers compare representations, not to imply another supported backend.

## Tools around the model

| Tool | Useful role | Current relationship |
| --- | --- | --- |
| [Spark](https://github.com/sparkjsdev/spark) | Gaussian rendering integrated with Three.js | Installed viewer dependency |
| [Three.js](https://github.com/mrdoob/three.js) | Cameras, WebGL scene and controls | Installed viewer dependency |
| [SuperSplat](https://github.com/playcanvas/supersplat) | Inspect, crop, clean and publish Gaussian scenes | External companion; no API integration |
| [Brush](https://github.com/ArthurBrussee/brush) | Cross-platform Gaussian reconstruction experiments | Alternative workflow; not an included backend |

Export/import compatibility is version- and attribute-dependent. Test an actual artifact instead of assuming that a shared extension guarantees interoperability.

## A practical evaluation plan

1. Use the same consented static capture set for all methods. Keep source clips, selected frames and held-out views identifiable.
2. Record model/checkpoint revision, dependencies, GPU, precision, frame budget and resolution. Separate cold-start weight downloads from inference time.
3. Complete the [GPU acceptance checklist](GPU_ACCEPTANCE.md) before quality comparisons. Inspect wall continuity, duplicate objects, holes and camera navigation.
4. Use held-out view metrics only with appropriate reference images and comparable cameras. PSNR/SSIM/LPIPS measure aspects of rendered appearance, not physical dimensions or navigability.
5. With calibrated ground truth, assess geometry and scale separately. Without it, describe qualitative findings without inventing numerical accuracy.
6. Measure upload time, model time, peak VRAM, output size, browser load time and frame rate separately. Include failure cases and the target browser/device.
7. Change one stage at a time: backend first, then alignment, then optional refinement. Keep the original output for comparison.

The plan above is proposed work. No populated WolfWorld benchmark table exists yet.

## License and citation boundaries

Original application code is MIT-licensed. That does not override model weights, model source, datasets, sample media or dependency terms. HY-World uses upstream Tencent terms; DA3's model table distinguishes licenses by variant; VGGT has its own current license. Consult the exact revision and checkpoint for your intended use. See [third-party notices](THIRD_PARTY.md).

Cite the original methods actually used in your experiment. [CITATION.cff](../CITATION.cff) identifies WolfWorld as software and does not substitute for model-paper citations. Project and paper links here are acknowledgments, not endorsements by their authors.
