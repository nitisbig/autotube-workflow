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

## Animation

`available-space` is the default for all boards. Scene 1 draws on the empty
board; scenes 2–4 draw below the completed top-row drawings; scene 5 uses the
remaining lower-right area; scene 6 draws in its final cell. Artwork retains its
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

The current project contains 72 scenes/12 boards. Its configuration is aligned
to the supplied Nietzsche word SRT and 402.984-second recording; eleven board
pauses produce a 416.184-second output. Source recordings/subtitles are intact.
Do not use script planning estimates as final recorded timestamps.
