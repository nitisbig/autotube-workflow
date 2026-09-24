Generate a complete edits.json for a video using the four attached files:

  - script.md: narration, beat order, and visual descriptions
  - subtitle.srt: timing generated from the original audio
  - editor.py: the authoritative JSON schema and renderer behavior
  - sample_edits.json: the reference editing style and default settings

  Read all four files completely. Produce a new configuration in one pass. Do not reuse the sample’s narration, scene count, timestamps, camera keyframes, or duration.

  Follow editor.py for required fields, valid values, units, and validation rules. Copy compatible presentation and encoding settings from sample_edits.json. Use project-relative asset paths
  following the sample’s naming convention. If assets are not supplied, label inferred paths as assumptions in notes.

  Create one scene for each script beat and four sections for its four visual reveals, unless editor.py requires a different structure. For this editor, use section rectangles [0,0,0.25,1],
  [0.25,0,0.5,1], [0.5,0,0.75,1], and [0.75,0,1,1]. Number scenes and sections sequentially.

  Align each section’s narration with subtitle.srt in chronological order. The SRT is the timing authority. A script sentence may span several cues, and one cue may contain parts of two
  sections. Match wording by context despite punctuation differences, numerals, or minor transcription errors. Use the script’s intended wording for narration and the SRT’s timestamps for
  timing.

  Use a cue’s exact start time when a section begins at a cue boundary. If a section begins partway through a cue, estimate its start proportionally from the number of words before that
  boundary. Record whether each start came from a cue boundary or an estimate in timing_source, following the sample’s format. Never describe an estimated word boundary as exact.

  Use absolute seconds. Set each section’s end to the next section’s start, including across scenes. Set the first section’s start to 0. Set the final section’s end and output.duration to
  the final SRT timestamp. This duration comes from the audio-generated subtitles; do not copy the sample duration. If editor.py’s audio-duration check later fails because the audio extends
  beyond the last subtitle, report that the measured audio duration is needed to correct output.duration.

  Match the sample’s reveal rhythm where timing permits: roughly 0.22 seconds of hold after sections 1 and 3, 0.80 seconds after sections 2 and 4, and 0.60-second camera slides. Shorten
  these when necessary to preserve narration timing. Every section must satisfy start < draw_end <= end.

  Rebuild the camera keyframes for the new scenes. Camera x is measured in screen widths. Start at time 0, x=0. For each later scene with zero-based index i, slide from x=i-1 to x=i-0.5
  before its first section starts, then from x=i-0.5 to x=i before its third section starts. Hold the camera steady between slides. Finish each preceding reveal before its slide begins. Keep
  keyframe times strictly increasing and x positions nondecreasing. Hold the final position through the end.

  Keep the sample’s compatible canvas, hand, reveal, output, and audio settings. Only preserve the hand tip coordinates if using the same hand image. Do not invent features unsupported by
  editor.py.

  Before output, check that the JSON parses, all required fields are present, all beats and visuals are covered, sections are chronological and contiguous, paths and rectangles are valid,
  camera keys satisfy editor.py, and the last section ends at output.duration. If the files and execution tools are available, save edits.json and run `python3 editor.py --config edits.json
  --validate`; fix any configuration errors. Do not render the video.

  Return the complete edits.json only, with no Markdown fence, commentary, placeholders, or omitted scenes. Put any necessary assumptions or validation limitations in its notes field.
