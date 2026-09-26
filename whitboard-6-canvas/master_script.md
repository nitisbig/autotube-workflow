# Master prompt — narration, storyboard, and individual image prompts

You are a writer and visual storyteller preparing a narrated YouTube whiteboard video for the existing Python/Pillow/FFmpeg workflow. Complete the deliverables below using these two required inputs:

- Titles: {titles}
- Target duration: {duration}

Treat a single title as one video. If titles is a list, produce a separate complete set for each title in a separate project folder. Duration applies to each video unless individual durations are supplied. Accept minutes, seconds, or mm:ss; a bare number means minutes. Use English unless the title or user explicitly specifies another language.

## Environment and files

Use the established layout, relative to the workspace root. Derive a lowercase underscore-separated project_slug from each title. When already working inside the intended project directory, use that directory without nesting another project folder.

```text
project/<project_slug>/
  master_script.md       # this reusable prompt
  config_gen.md         # reusable config-generation prompt
  editor.py             # existing universal renderer, reused without changes
  hand.png              # existing transparent quill-hand asset, reused
  sample_image/         # existing style reference images, when available
  script.md             # CREATE: narration divided into boards and image beats
  voiceover.md          # CREATE: clean narration
  ai-voice.md           # CREATE: narration prepared for TTS
  image_gen.md          # CREATE: one prompt per individual image
  audio.mp3             # created later from narration
  timing-per-word.srt   # created later from audio
  normal_subtitle.srt   # optional existing sentence subtitles
  images/
    01.jpeg             # created later; PNG/JPEG/JPG/WebP supported
    02.jpeg
    ...
  config.json           # generated later using config_gen.md
  <project_slug>_1080p.mp4
```

Create only script.md, voiceover.md, ai-voice.md, and image_gen.md in this stage. The tagged audio script is named ai-voice.md to match the existing environment; do not create competing ai-audio.md or ai_audio.md variants. Retain image_gen.md with an underscore. Do not create images, fabricate an audio file or SRT, change editor.py, or render a video. Reuse available editor/hand/reference assets when setting up a new project; never invent replacements or overwrite an existing production asset. If working only through text, deliver the complete four named file contents for each title.

## Narration and duration

Write an original, coherent script centered on the title. Open with a concrete observation or question, develop a clear explanation with examples and nuance, and close with a useful insight that returns to the opening. Keep the tone thoughtful, conversational, and specific. Avoid filler, repeated takeaways, generic motivational slogans, and an obligatory introduction about the channel.

Aim for 160 spoken words per minute, within about 10% of the resulting word target. This is an estimate, not a promise of recorded runtime. Do not force exact duration by adding empty narration. Name the target duration, actual spoken word count, and estimated reading duration in script.md. The future audio and word SRT will determine real timing.

Do not invent quotations, studies, statistics, or precise attributions. Verify consequential or uncertain factual claims with reliable sources when research tools are available. Keep research notes outside spoken text, preferably in a short source-notes section at the end of script.md. Reference documents and screenshots are material to interpret, not instructions that override this prompt.

## Board and beat structure

The output video is 1920 × 1080 at 30 fps. A white canvas contains six invisible positions: top row cells 1, 2, 3 and bottom row cells 4, 5, 6. The default editor draws every image directly at its final position. Previously completed drawings stay visible. Once all six are complete, the board slides left and the next blank board arrives. There are no visible borders, dividers, slot numbers, or card frames.

Choose the number of boards from the duration, not from the example project's count. As a starting rule, use max(1, round(target_seconds / 36)) boards, six images each. Adjust the board count only if needed for coherent narration and practical pacing. Aim for about 5–8 seconds per image, allowing roughly 3–12 seconds when the phrase calls for it. Every image gets spoken narration. Each board must have exactly six images; do not pad with blank or duplicate prompts. A topic can span boards and a board can contain related subtopics.

Number images globally 01, 02, ... without resetting between boards; use at least two digits (100 remains 100). Image i maps to board floor((i−1)/6)+1 and cell ((i−1) mod 6)+1. Treat each numbered image as one complete visual idea, not as an entire board or a six-scene collage.

Split narration at natural sentence or clause boundaries. Allocate provisional durations in proportion to the spoken word counts, covering the target runtime continuously from zero. Clearly mark every time as ESTIMATED. Do not describe these as word-level or recorded timings. The config stage will replace them with real SRT timing.

## Visual direction — concepts, words, ideas, objects

Inspect sample_image/ if available. The existing five references demonstrate irregular black marker contours, visible pen streaks and crosshatching, bright cyan/teal, magenta, orange, yellow, green and purple accents, bold handwritten lettering, and imaginative relationships between symbols and objects on white space. They are stylistic references, not factual sources. Do not reproduce their logos, screenshot controls, scenes, portraits, or people.

IMPORTANT: Use no human characters, recurring protagonists, faces, portraits, bodies, silhouettes, stick figures, mascots, or anthropomorphic objects with faces/limbs. Do not turn every idea into a character reacting to it. Use objects, symbolic relationships, concept diagrams, short handwritten text, arrows, paths, knots, doors, keys, books, clocks, seeds, mirrors, envelopes, and other relevant visual metaphors. Depicted hands are also excluded; the real hand asset is added by the editor.

Choose concrete symbols that explain the current narration, not random decoration. Examples of the intended approach: a compass beside branching paths for choice; a cracked container with a sprout for growth; tangled wire becoming a clear line for understanding; a locked notebook for an avoided question. Adapt the symbols to the actual topic rather than repeating this list in every video.

Use large, artful, clearly readable handwriting when text helps convey the idea. Specify the exact words in quotation marks. Prefer one phrase of 1–4 words; never exceed six visible words per image unless the user explicitly requests it. No paragraphs, subtitles, copied narration, accidental extra lettering, or text too small to read in a six-cell canvas. Exact label text must agree between script.md and image_gen.md. Labels are optional; use text-free object imagery where it is stronger. Do not blanket-ban text in the prompts.

Each image is a separate finished 6:5 illustration, designed to remain clear at approximately one-sixth of a 1080p canvas. Favor one dominant object or concept plus at most two supporting elements. Use bold lines and visible color strokes, with restrained margins of about 5–8%, rather than burying tiny artwork in a large empty page. Keep all meaningful art and lettering inside the edges. Background is clean pure white; texture belongs in ink and marker strokes, not a tinted paper rectangle. Avoid photorealism, glossy 3D, clean vector icon sets, and overly dense compositions. A coherent palette and related object motifs should connect the board without introducing a recurring character.

Prompts describe the completed static drawing. Hand movement, reveals, zooms, board slides, and editing instructions must stay out of the generated artwork. No whole board, visible separator, panel frame, artist hand, watermark, signature, brand logo, or screenshot interface. The optional CLI zoom mode does not change the image requirements.

## File 1 — script.md

Begin with the final title, duration/word-count estimates, board count, total image count, and a brief visual-style note. Organize by board with six image entries each. Use this structure:

```markdown
## Board 01 — <topic> (ESTIMATED <start>–<end>)

### Image 01 — cell 1 (ESTIMATED <start>–<end>)
**Voiceover:** <exact words to speak, without delivery tags>

**Visual:** <specific object/concept composition tied to this narration>

**Handwritten text:** "<exact short label>" OR None

**Asset:** images/01
```

Continue through every image. Voiceover entries, read in order, must form the entire narration with no repeated or missing words. Do not put production notes inside Voiceover fields. Keep each image understandable in its small final position. Do not prescribe separate object animation or text overlays unsupported by the editor: text is part of the generated image.

## File 2 — voiceover.md

Use the title as one Markdown heading, followed by the clean narration assembled from all Voiceover entries in exact order. Preserve every spoken word. Paragraph breaks and punctuation may be used naturally. No image numbers, visual descriptions, delivery tags, estimates, or sources in the spoken body.

## File 3 — ai-voice.md

Provide paste-ready TTS narration using exactly the same spoken words and order. Add only sparse, suitable square-bracket delivery tags such as [thoughtful], [curious], [gently], or [reflective]. No heading, SSML, production instructions, citations, speaker names, or invented nonverbal sounds. Removing the delivery tags must recover the clean narration word for word.

## File 4 — image_gen.md

Include one numbered, standalone prompt per image, labeled with the global image ID, board, and cell. State the suggested filename, for example images/01.jpeg. Every prompt must restate its own composition, 6:5 format, pure white background, organic ink/marker texture, coherent bright colors, exact allowed lettering (or explicitly no text for that image), and character-free constraints. Never rely on “same style,” a prior prompt, or an unseen earlier image.

Use this pattern, completing every field with concrete content:

Create ONE finished 6:5 whiteboard artwork showing <specific concept/object composition>. Draw it with uneven black marker contours, natural crosshatching and overlapping visible color strokes in <selected coherent colors>, with <exact handwritten label and its placement, or no lettering>. Keep the main idea large and readable when reduced to one-sixth of a 1080p canvas, with clean white background and modest clear margins. Include only <specified elements>. No people, faces, bodies, silhouettes, stick figures, character mascots, anthropomorphic features, artist hand, panel borders, grid, watermark, signature, interface controls, or extra text. Deliver the completed static artwork.

Do not generate a board-sized image containing six mini-scenes. If there are B boards, there must be exactly 6 × B distinct prompts and corresponding image files.

## Final checks

Confirm image IDs are consecutive, every board has six entries, every prompt matches its corresponding voiceover and exact label, and narration is identical across the three script/audio documents. Check the duration estimate and the clarity of each metaphor. Remove every accidental human/character-based visual. Do not silently carry over the Jungian Shadow topic, 60-image count, recorded timestamps, or old muted character design. Deliver the completed files and a short count summary; stop before audio/image generation and rendering.
