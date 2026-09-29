# Video editor

Run from the project root (Python 3, Pillow, FFmpeg and ffprobe required):

```bash
python3 editor.py --validate
python3 editor.py
python3 editor.py --res 2k --fps 25
python3 editor.py --res 4k --fps 60
python3 editor.py --start 3 --duration 4 --output preview.mp4
python3 -m unittest discover -s tests
```

Defaults: 1920×1080 at 30 FPS from config.json. `--res 2k` means QHD
2560×1440; `4k` means UHD 3840×2160. FPS choices are 25, 30 and 60.
Overrides are applied in memory; config.json stays unchanged. Export overrides
add a resolution/FPS suffix to the configured filename. `--output` overrides
that filename and resolves relative to the working directory. Existing outputs
require `--overwrite`. Configuration/media paths resolve relative to config.json.

## AMD GPU export (Linux)

```bash
python3 editor.py --gpu true --validate
python3 editor.py --gpu true --duration 5 --output gpu-preview.mp4
python3 editor.py --gpu true
python3 editor.py --gpu false
```

GPU mode uses FFmpeg `h264_vaapi` with Mesa VA-API and defaults to
`/dev/dri/renderD128`. Select another device with `--gpu-device /dev/dri/renderD129`.
The kernel `amdgpu` driver alone does not guarantee H.264 encoding support;
FFmpeg, the userspace VA-API driver and device permissions must also support it.
Before preparing audio or rendering, a three-frame encoding test checks the
requested resolution and frame rate. `--validate --gpu true` runs this test too.
If it fails, the command reports the FFmpeg error and exits; CPU fallback is
explicit with `--gpu false` (also the default).

GPU encoding uses constant QP 20 and disables B-frames for compatibility with
older AMD hardware. CPU `output.crf` and `output.preset` do not apply in GPU mode;
quality and file size will differ. MP4/H.264, AAC audio and color conversion are
preserved. Pillow drawing, compositing, RGB conversion and audio processing
still run on the CPU: GPU encoding can shorten export time but does not guarantee
a faster overall render. Start with 1080p; older GPUs may reject 2K/4K exports.

## Animation

`available-space` is the default for all boards. Scene 1 draws on the empty
board; scenes 2–4 draw below the completed top-row drawings; scene 5 uses the
remaining lower-right area; scene 6 draws slightly inset within its final cell when the swipe hand is enabled. Artwork retains its
aspect ratio. Completed drawings remain visible. The existing raster brush
reveal approximates drawing, rather than reconstructing original pen strokes.

`animation.pause_seconds` (0.5) holds the completed drawing before placement;
`animation.move_seconds` (0.6) controls the smooth move into its original cell.
These phases fit within each scene's narration interval. For unusually short
scenes both durations scale proportionally, reserving half the interval for
drawing. No silence is added for these scene holds. The separate existing
1.2-second board changes include inserted narration silence and bird SFX.

`--mode canvas` and `--mode zoom-up-draw` preserve the previous modes.

## Module map and extension points

- `cli.py`: arguments, export overrides, default config path.
- `validation.py`: configuration and media preflight.
- `renderer.py`: renderer state and frame composition.
- `modes.py`: drawing layouts, phase allocation, `MODES` registry. Register a
  function `(renderer, beat_index, absolute_time) -> PIL.Image` to add a custom
  mode; its key becomes a CLI choice. Handlers must return an RGB output frame.
- `animation.py`: brush trajectory and raster reveal; change `DrawingMixin`
  to implement a new drawing animation.
- `transitions.py`: bird/page movement in `TransitionMixin`; board transition
  dispatch lives in `Renderer.frame`, with the plain slide fallback in
  `Renderer.drawing_frame`. Keep transitions inside slide_start/end so audio
  remains aligned.
- `artwork.py`: asset fitting, margin trimming, thumbnails and board composition.
  Existing `artwork`, `board`, `hand`, and `reveal` config fields control style.
- `overlays.py`, `gif.py`: anchored hands and timed bird sprites.
- `geometry.py`: interpolation/easing shared by modes and transitions.
- `audio.py`: source-to-output pauses, audio fades and sound effects.
- `media.py`: image resolution and ffprobe helpers.
- `export.py`: streamed frames, audio seeking and atomic FFmpeg export.

The current project contains 90 scenes/15 boards. Its configuration is aligned
to the supplied Jung shadow word SRT and 506.448-second recording; fourteen board
pauses produce a 523.248-second output. Source recordings/subtitles are intact.
Do not use script planning estimates as final recorded timestamps.

## Swipe hand

`swipe_hand` is an optional top-level config object: `enabled` (default false),
`path` (relative to config), `tip` (two normalized coordinates in the original
asset), and `height_fraction` (screen-height fraction, greater than 0 and at most 2).
This project uses `swipe-hand.png`, tip `[0.72, 0.10]`, height `0.65`.
The separate drawing hand remains unchanged. The swipe hand follows the finished
artwork during available-space placement and zoom-up-draw shrink, fading on
contact and release. The sixth available-space drawing starts 5% inset on each
side so it also settles into its cell. Canvas mode has no placement phase.
Placement uses existing phase budgets and never adds narration pauses.
