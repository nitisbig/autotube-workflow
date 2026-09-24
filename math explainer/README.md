# Local math explainer

`editor.py` renders any lesson expressed in its supported JSON object/action vocabulary. `config.json` is the current Newton's second law lesson. `sample_config.json` is a complete example for future LLM use. `config_gen.md` is the master prompt and schema reference. The original narration, word subtitles, audio and `main.py` are preserved.

## Render

From this directory:

```bash
python3 editor.py --validate
python3 editor.py
python3 editor.py --mode advanced --duration 10
# Full advanced rendering is also supported:
python3 editor.py --mode advanced
```

The host needs Python 3, FFmpeg/ffprobe, and access to Docker. Your installed Manim Community 0.21.0 image is selected by local image ID in the config (no download required). On another machine, change `docker_image` to a locally installed image such as `manimcommunity/manim:0.21.0`. The container runs as your user, with no network and only this project mounted. All assets must be within this directory for Docker rendering. Keep editor.py beside the config. An alternative with Manim, LaTeX, fonts and FFmpeg installed natively is `python3 editor.py --local`.

To change only encoding settings after a successful render, use `--encode-only` with the same config, mode, duration and output arguments. This reuses existing pictures; visual or timing changes require a normal render.

Outputs are under `output/`; intermediates and the resolved timeline are under `build/`. Each output includes an MP4, a phrase-grouped SRT and an ffprobe report. Use `--output output/custom.mp4` to choose a filename. Output paths for Docker must remain inside the project. Existing outputs with the same name are replaced. Audio starts at time zero without speed changes. Preview rendering cuts picture, audio and captions together. Captions are selectable in MP4 and available separately for YouTube upload, leaving diagrams unobscured.

Default export: 1920×1080, 16:9, 30 fps, H.264 High Profile, CRF 18, yuv420p, BT.709 metadata, AAC 320 kb/s stereo at 48 kHz, faststart MP4. The low-core machine uses two FFmpeg encoding threads. Manim Cairo renders both modes on CPU; advanced means real shaded 3D objects, not a GPU requirement. It uses a front orthographic camera and rotated objects to preserve legible equations.

## Next lesson

1. Replace voiceover.md, audio.mp3 and audio.srt.
2. Give your LLM config_gen.md and those text inputs plus sample_config.json; specify basic or advanced (basic by default).
3. Save its JSON to config.json, validate, then render. Review the actual video for mathematical and visual quality.

Timing anchors use SRT cue IDs; numeric timestamps are also supported. Events are snapped to the nearest frame, preventing accumulated timing drift. Actions within an event animate together; events cannot overlap. The editor deliberately accepts declarative primitives, not executable code. New concepts can combine equations, shapes, graphs and motion; new primitive types require an editor extension. See config_gen.md for the complete contract.

The supplied SRT says “E” in cue 7; displayed captions correct this to “F” using config, without editing source files. Its tiny word overlap is tolerated for caption grouping. Source audio duration is approximately 79.464 seconds, so final video/audio durations can differ by one output frame due to frame quantization.

This project uses [Manim Community](https://docs.manim.community/en/stable/), matching your installed Docker image. [3Blue1Brown's Manim](https://github.com/3b1b/manim) is a separate implementation; the explanatory approach is inspired by the channel.
