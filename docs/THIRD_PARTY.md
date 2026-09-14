# Third-party components and assets

WolfWorld's root MIT license covers original application code and documentation. It does not relicense upstream models, weights, dependencies, datasets or sample media. Preserve each component's notices when redistributing it. Versions below describe this checkout; check the lockfile and pinned worker revision for reproducibility.

## Application and build dependencies

| Component | Relationship | Upstream |
| --- | --- | --- |
| Spark 2.1.0 | Gaussian browser renderer; MIT code | [sparkjsdev/spark](https://github.com/sparkjsdev/spark) |
| Three.js | WebGL scene, cameras and controls; MIT code | [mrdoob/three.js](https://github.com/mrdoob/three.js) |
| React / Next.js / Vinext / Vite | Frontend and Worker build stack | See `package.json` and `pnpm-lock.yaml` for resolved packages and their notices |
| shadcn components | Vendored UI primitives | [shadcn-ui/ui](https://github.com/shadcn-ui/ui); [vendored license](../vendor/shadcn-tailwind-4.13.0.LICENSE.md) |
| Sites Vite plugin | Vendored local auth/build support; MIT, OpenAI | [included notice](../build/sites-vite-plugin.LICENSE) |
| Drizzle / Cloudflare tooling | Database schema and Worker/storage integration | See the lockfile and upstream package notices |

## Reconstruction environment

- [HY-World 2.0 / WorldMirror](https://github.com/Tencent-Hunyuan/HY-World-2.0): installed separately at the worker's pinned revision; source and model weights retain Tencent's upstream terms. Weights are not committed here.
- [gsplat](https://github.com/nerfstudio-project/gsplat): installed in the model environment; Apache-2.0 code. Its use as an upstream dependency does not mean WolfWorld implements a separate refinement stage.
- [PyTorch](https://github.com/pytorch/pytorch), [FlashAttention](https://github.com/Dao-AILab/flash-attention), [CuPy](https://github.com/cupy/cupy), NumPy and Pillow retain their upstream notices. The worker Dockerfile specifies its dependencies independently of the web lockfile.
- [FFmpeg](https://ffmpeg.org/legal.html): separately installed video tooling; licensing depends on the build configuration. This repository does not bundle FFmpeg binaries.

## Sample scene and artwork

`public/samples/butterfly.spz` is the [official Spark butterfly sample](https://sparkjs.dev/assets/splats/butterfly.spz), retained from the original WolfWorld application. The interface links to Spark and identifies it as sample data, not a reconstruction of uploaded videos. The application MIT license does not grant additional rights to third-party sample content; consult its upstream provenance/terms before reusing it outside this demonstration.

`docs/assets/wolfworld-banner.svg` is original project artwork under the root MIT license. It is a conceptual illustration, not a model output or accuracy example.

## Research references, not installed backends

[Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3), [VGGT](https://github.com/facebookresearch/vggt), [DUSt3R](https://github.com/naver/dust3r), [COLMAP](https://github.com/colmap/colmap), [Brush](https://github.com/ArthurBrussee/brush), [SuperSplat](https://github.com/playcanvas/supersplat) and [NeRF](https://github.com/bmild/nerf) appear as research or companion-tool links. Their code is not vendored as a WolfWorld backend. Model/checkpoint licenses can differ from repository code licenses; use the exact chosen release's terms.

See [RESEARCH.md](RESEARCH.md) for paper references and current integration boundaries. None of these acknowledgments imply affiliation or endorsement.
