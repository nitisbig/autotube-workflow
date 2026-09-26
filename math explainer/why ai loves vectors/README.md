# Vectors in AI — animation

Run from this folder (or use the absolute path to editor.py).

```sh
python3 editor.py
```

Exports the complete audio-length video to `output/vectors_ai_basic.mp4` using the installed Manim Docker image. Default: 1920×1080, 30 fps, H.264, AAC audio, black background. No captions are burned into the picture.

## Preview and customization

```sh
python3 editor.py --duration 10
python3 editor.py --resolution 4k --fps 60
python3 editor.py --duration 10 --resolution 720p --output output/draft.mp4
python3 editor.py --subtitles
python3 editor.py --validate
python3 editor.py --audit-layout
```

`--subtitles` adds an optional selectable subtitle track grouped from the word cues. `--local` uses a local Manim installation instead of Docker. `--config` selects another storyboard JSON. `--output` sets the MP4 path. Docker exports must stay inside the project folder.

## Timing and design

`cue-per-word.srt` is the animation timing authority. Each storyboard event references a word cue ID; timings round to the nearest video frame. The normal subtitles and voiceover script were used to understand the narrative, not as a replacement timing source. Audio is muxed from the original recording starting at time zero.

`generate_config.py` authors the entire storyboard; run it to regenerate `config.json` after changing the story or replacing word cues. Edit the theme, export settings, and object specifications in `config.json` for smaller adjustments. Regeneration overwrites that JSON.

Style is adapted from sample-frames: black canvas, restrained blue grids, yellow/blue vectors, white serif labels and LaTeX equations. Only key words and visual labels appear. Embedding coordinates, attention, and probabilities are illustrative examples, not measured model outputs.

Only the opening 10 seconds have been exported for visual testing. The full timeline is validated and its text/frame bounds audited without rendering the full video. That audit checks label collisions and safe frame bounds; intentional diagram intersections and text inside containers are allowed. It does not replace reviewing every animation in the final export.

Previous calculus-specific scripts are preserved in `archive/`. The old `sample_config.json` and `config_gen.md` are legacy references, not inputs for this video.
