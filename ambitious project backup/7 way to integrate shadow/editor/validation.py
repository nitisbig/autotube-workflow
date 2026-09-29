import math
import shutil
from .media import probe, resolve_image
from .audio import audio_pauses
PHASES = ('start', 'draw_start', 'draw_end', 'shrink_start', 'shrink_end', 'slide_start', 'end')
def validate(c, base):
    def need(condition, message):
        if not condition:
            raise ValueError(message)
    need(c['schema_version'] == 1, 'Unsupported config schema_version')
    for program in ('ffmpeg', 'ffprobe'):
        need(shutil.which(program), f'Install {program} and put it on PATH')
    from .modes import MODES
    animation = c.get('animation', {})
    need(animation.get('mode', 'available-space') in MODES, 'Unknown animation.mode')
    for key, default in (('pause_seconds', .5), ('move_seconds', .6)):
        value = animation.get(key, default)
        need(isinstance(value, (int, float)) and math.isfinite(value) and value > 0,
             f'animation.{key} must be finite and positive')
    o = c['output']
    need(all(isinstance(o[k], int) and o[k] > 0 for k in ('width','height','fps')), 'Invalid output dimensions/fps')
    need(o['width'] % 2 == o['height'] % 2 == 0, 'H.264 requires even dimensions')
    need(o['width'] * 9 == o['height'] * 16, 'Output must be 16:9')
    need(o['fps'] <= 60, 'Supported frame rate is 1–60 fps')
    need(0 <= o['crf'] <= 51, 'CRF must be between 0 and 51')
    need((base / c['audio']['path']).is_file(), 'Audio file is missing')
    duration = float(probe(base / c['audio']['path'])['duration'])
    pauses = audio_pauses(c)
    for key in ('transition_fade_out', 'transition_fade_in'):
        value = c['audio'].get(key, 0)
        need(math.isfinite(value) and 0 <= value <= 2, f'Invalid {key}')
    sfx = c['audio'].get('transition_sfx', {})
    if sfx.get('path'):
        need((base / sfx['path']).is_file(), 'Missing transition sound effect')
        need(0 <= sfx.get('source_start', 0) < float(probe(base / sfx['path'])['duration']),
             'Transition sound source_start is outside the audio')
        need(0 < sfx.get('volume', .8) <= 2, 'Invalid transition sound volume')
        for key in ('fade_in', 'fade_out'):
            need(0 < sfx.get(key, .1) <= 1, f'Invalid transition sound {key}')
    source_duration = c['audio'].get('source_duration', c['duration'])
    need(abs(duration - source_duration) <= .15, 'Configured source duration differs from audio by more than 0.15 seconds')
    previous_pause = 0.0
    for pause in pauses:
        need(math.isfinite(pause['source_time']) and math.isfinite(pause['duration']) and
             previous_pause < pause['source_time'] < source_duration and pause['duration'] > 0,
             'Audio pauses must have increasing source times and positive durations')
        previous_pause = pause['source_time']
    need(abs(source_duration + sum(p['duration'] for p in pauses) - c['duration']) < .001,
         'Video duration must equal source audio plus inserted pauses')
    bird = c.get('jackdaw', {})
    if bird.get('enabled', False):
        for key in ('watching_path', 'flying_path'):
            need((base / bird[key]).is_file(), f'Missing jackdaw asset: {bird[key]}')
        need(0 < bird['watching_height_fraction'] <= .2 and
             0 < bird['flying_height_fraction'] <= .3, 'Invalid jackdaw size')
        need(len(bird['beak']) == 2 and all(0 <= x <= 1 for x in bird['beak']), 'Invalid jackdaw beak anchor')
    need(c['board']['columns'] == 3 and c['board']['rows'] == 2, 'This editor uses a 3 by 2 grid')
    need(0 < c['board']['margin_fraction'] < .1 and 0 < c['board']['cell_padding_fraction'] < .2, 'Invalid board margins')
    need(0 < c['reveal']['brush_fraction'] <= .3 and 0 < c['reveal']['row_spacing'] <= 1, 'Invalid reveal settings')
    need(len(c['focus']['rect']) == 4, 'focus.rect must be [left, top, right, bottom]')
    x0,y0,x1,y1 = c['focus']['rect']
    need(0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, 'Invalid focus rectangle')
    if c['hand']['enabled']:
        need((base / c['hand']['path']).is_file(), 'Hand image is missing')
        need(len(c['hand']['tip']) == 2 and all(0 <= x <= 1 for x in c['hand']['tip']), 'Invalid normalized hand tip')
        need(0 < c['hand']['height_fraction'] <= 2, 'Invalid hand size')
    beats = c['beats']
    swipe = c.get('swipe_hand', {})
    need(isinstance(swipe, dict), 'swipe_hand must be an object')
    need(not set(swipe) - {'enabled', 'path', 'tip', 'height_fraction'}, 'Unknown swipe_hand setting')
    need(isinstance(swipe.get('enabled', False), bool), 'swipe_hand.enabled must be boolean')
    if swipe.get('enabled', False):
        need(isinstance(swipe.get('path'), str) and (base / swipe['path']).is_file(),
             'Missing swipe_hand.path asset: ' + str(swipe.get('path')))
        tip = swipe.get('tip')
        need(isinstance(tip, list) and len(tip) == 2 and
             all(isinstance(x, (int, float)) and math.isfinite(x) and 0 <= x <= 1 for x in tip),
             'swipe_hand.tip must contain two normalized coordinates in [0,1]')
        height = swipe.get('height_fraction')
        need(isinstance(height, (int, float)) and math.isfinite(height) and 0 < height <= 2,
             'swipe_hand.height_fraction must be finite and in (0,2]')
        from PIL import Image
        with Image.open(base / swipe['path']) as im:
            im.verify()
    need(len(beats) > 0 and len(beats) % 6 == 0, 'Every board must contain exactly six images')
    previous = 0.0
    for i,b in enumerate(beats):
        need(b['id'] == i+1 and b['board'] == i//6+1 and b['cell'] == i%6+1, 'Beat IDs, boards and cells must be sequential')
        ts = [b[k] for k in PHASES]
        need(all(math.isfinite(x) for x in ts) and all(a <= z for a,z in zip(ts,ts[1:])), f'Invalid phases for image {b["id"]}')
        need(b['draw_start'] < b['draw_end'] and b['shrink_start'] < b['shrink_end'], f'Empty drawing/shrink phase for image {b["id"]}')
        need(abs(b['start']-previous) < .001, f'Timeline gap or overlap at image {b["id"]}')
        need(b['cell'] == 6 or abs(b['slide_start']-b['end']) < .001, 'Only completed boards can slide')
        resolve_image(base, b['image'])
        previous = b['end']
    need(abs(previous-c['duration']) < .001, 'Last beat must end at duration')
    need(abs(beats[-1]['slide_start']-beats[-1]['end']) < .001, 'Final board must remain on screen')
    if bird.get('enabled', False) or pauses:
        slides = [b for b in beats if b['slide_start'] < b['end']]
        need(len(slides) == len(pauses) == len(beats)//6-1,
             'Each board change requires one matching narration pause')
        offset = 0.0
        for beat, pause in zip(slides, pauses):
            need(abs(beat['slide_start']-(pause['source_time']+offset)) < .001 and
                 abs(beat['end']-beat['slide_start']-pause['duration']) < .001,
                 'Board pull must coincide exactly with inserted silence')
            offset += pause['duration']
    return c['duration']
