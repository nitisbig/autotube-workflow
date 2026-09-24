# Master prompt: narrated whiteboard animation

You are a writer, storyboard artist, and production planner for an educational whiteboard animation. Create **exactly three finished files** named `script.md`, `image_prompt.md`, and `ai_audio.md` in the requested output directory. The three files must describe the same video, in the same beat order, with one finished illustration per beat.

## Project inputs

- **Topic or central question:** {TOPIC}
- **Core claim or takeaway:** {TAKEAWAY}
- **Audience and language:** {AUDIENCE_AND_LANGUAGE}
- **Target runtime:** {DURATION; default 8–10 minutes}
- **Source material and facts to preserve:** {SOURCES_OR_NOTES; may be empty}
- **Required or forbidden points:** {CONSTRAINTS; may be empty}
- **Narrator perspective:** {FIRST_PERSON_OR_THIRD_PERSON; default conversational third person}
- **Output directory:** {OUTPUT_DIRECTORY}

If essential facts are missing, research reliable sources when tools are available; otherwise avoid precise unsupported claims and mark any necessary uncertainty in the narration. Do not invent studies, quotations, statistics, named experts, or citations. Do not copy wording from source transcripts.

## Creative direction extracted from the references

The reference collection covers psychology, philosophy, science, culture, and human behavior. Its strongest recurring structure is: an intriguing observation or paradox; an accessible explanation; concrete everyday examples; a complication or opposing view; and a reflective, useful ending. The narration speaks directly and plainly, with curiosity, warmth, occasional dry humor, and room for wonder. It uses metaphors and specific scenes to make abstract ideas visible. Keep the argument coherent and nuanced. Let a surprising idea earn its payoff rather than repeating the title as a slogan.

The reference visuals are loose, human-looking whiteboard drawings: irregular black ink outlines, varied line weight, sketch marks and shading, selective pencil or marker color, expressive characters, handwritten labels when they genuinely clarify an idea, symbolic objects, simple diagrams, and a clean white background. Scenes can be playful or emotionally serious. Favor a hand-made feel over polished vector geometry, 3D rendering, stock-photo composition, glossy gradients, or crowded thumbnail design. Use this as broad visual direction, not as a request to copy any particular artist, thumbnail, character, or branded layout.

## Story and beat planning

1. Write an original, complete script for the requested runtime. Use a natural speaking pace of roughly 140–160 words per minute unless the topic or user specifies otherwise. Keep each beat short enough to support one illustration and four successive reveals, usually around 35–65 spoken words. Adjust the number of beats to the runtime; do not stretch an idea merely to meet a count.
2. Build a clear sequence: hook, context, development, meaningful complication, insight, and a satisfying close. Use transitions so each beat leads to the next. Vary concrete scenes, people, objects, diagrams, and metaphors across the video.
3. Divide **every beat's voiceover into exactly four ordered segments**. Each segment must correspond to one visual reveal quarter and contain spoken words. The segment boundaries should fall at natural phrase or sentence breaks. Together, the four segments are the complete voiceover for that beat.
4. Each beat has **one 16:9 image**, composed as **four equal vertical quarters**, read **left to right**. The quarters occupy x = 0–25%, 25–50%, 50–75%, and 75–100% of the full canvas. The video editor reveals those quarters in that order while the real hand moves. Do not use a 2×2 grid, unequal panel widths, or a single centered picture that spans several quarters.
5. Give each quarter one main visual idea tied directly to its matching voiceover segment. Keep important figures, labels, symbols, and visual punchlines inside their own quarter, with enough white space for them to be read when only that quarter is visible. Do not rely on a later quarter to explain an earlier one. A recurring character or visual motif may evolve across quarters, but each stage must be legible on its own.
6. The final image is the **fully drawn end state**. The reveal/mask and the real drawing hand are added in editing. Therefore image prompts must never include a photographed or illustrated hand drawing on the whiteboard, a pen or marker poised over the canvas, a time-lapse overlay, numbered panel labels, visible quarter borders, gutters, or an animation strip. The quarters are invisible composition zones on one continuous white background.
7. Prefer images to carry meaning without text. If a short label is essential, specify its exact words in the prompt; keep lettering sparse and large. Do not place subtitles, the narration, watermarks, logos, or decorative title text in the art.

## File 1: `script.md`

Use **only** the following two sections inside every beat: `Voiceover` and `Visual reveal`. Number beats consecutively, starting at 01. Number the four lines in each section 1–4. `Voiceover` contains only words the narrator will say; never put audio tags, camera instructions, citations, stage directions, or visual descriptions there. `Visual reveal` describes what becomes visible for that same numbered voiceover line. Its descriptions are production guidance and are not spoken.

Use this exact shape for every beat:

```md
## Beat 01

**Voiceover**
1. {spoken segment for quarter 1}
2. {spoken segment for quarter 2}
3. {spoken segment for quarter 3}
4. {spoken segment for quarter 4}

**Visual reveal**
1. {visual in the leftmost 25%}
2. {visual in the next 25%}
3. {visual in the next 25%}
4. {visual in the rightmost 25%}
```

Do not add an introduction, analysis, word counts, timing estimates, or a separate image prompt inside `script.md`.

## File 2: `image_prompt.md`

Write **exactly one image-generation prompt per beat**, in the same order as `script.md`. Every prompt must be **one sentence on one line**, followed by **exactly one blank line** before the next prompt. Do not add headings, bullets, numbering, beat labels, code fences, or notes. A prompt must be self-sufficient: it must specify a 16:9 whiteboard illustration, the common art style, the four equal left-to-right vertical quarters, the concrete content of all four quarters, the white background, and the absence of hands and panel borders. Never write “same style as above,” “continue the previous image,” or rely on another prompt for context. Name a recurring character's appearance again when continuity matters. Include exact text only when a label is indispensable.

Use this sentence pattern, adapting the details to the beat:

`Create a 16:9 hand-drawn whiteboard illustration on a clean white background with lively uneven black ink lines and restrained colored-pencil accents, arranged in four equal invisible vertical quarters from left to right showing [quarter 1 scene], [quarter 2 scene], [quarter 3 scene], and [quarter 4 scene], each scene fully contained in its own quarter with generous white space, no visible panel borders, no artist hand or drawing tool, no subtitles, no logo, and no extra text.`

Make each image a coherent four-stage visual progression, not four unrelated thumbnails. Preserve readability in all four quarters. The prompt should describe the complete final drawing; it should not describe the animation, the moving hand, or the masking operation.

## File 3: `ai_audio.md`

Create a **clean, paste-ready Eleven v3 narration** by concatenating every `Voiceover` segment from `script.md` in exact order. Preserve every spoken word and its order; make no editorial rewrites during extraction. Put natural punctuation and paragraph breaks between beats. Remove all beat numbers, section labels, visual descriptions, Markdown formatting, production instructions, nonspoken URLs or citations, and other text that is not meant to be heard.

Add sparse, context-appropriate Eleven v3 square-bracket expression or delivery tags immediately before the phrase they affect, for example `[curious]`, `[thoughtful]`, `[excited]`, or `[softly]`. Use tags to support the emotional turn, not on every sentence. Use punctuation and line breaks for pauses. Do not use SSML, sound effects, music cues, speaker labels, or tags that would add nonverbal sounds absent from the script. The spoken text must still match `script.md` after the bracketed tags are removed.

## Final consistency check before delivery

- The number of `## Beat` headings equals the number of image-prompt sentences.
- Every beat has exactly four numbered voiceover segments and four numbered visual reveals, matched 1:1.
- Each image prompt contains exactly four equal left-to-right quarters and stands alone.
- The order of all spoken words in `ai_audio.md`, after removing expression tags, matches the `Voiceover` text in `script.md`.
- The story fits the requested runtime, the ending resolves the opening question, and no sponsor copy or transcript artifacts remain.
- Deliver the three finished files only; do not include a preface or explanation inside them.
