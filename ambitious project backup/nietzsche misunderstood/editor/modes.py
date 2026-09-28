"""Drawing mode registry. Handlers take (renderer, beat_index, absolute_time)."""
from PIL import Image
from .geometry import smooth, lerp_box


def available_box(renderer, cell):
    """Fit the artwork plane in unused space, matching the supplied six-step layout."""
    r = renderer
    left, top, right, bottom = r.board_rect
    gap = round(min(r.cw, r.ch) * r.c['board']['cell_padding_fraction'])
    if cell in (1, 2, 3):
        top += r.ch
    elif cell == 4:
        left += r.cw
        top += r.ch
    elif cell == 5:
        return r.cells[cell]
    left, top, right, bottom = left+gap, top+gap, right-gap, bottom-gap
    scale = min((right-left)/r.fw, (bottom-top)/r.fh)
    width, height = r.fw*scale, r.fh*scale
    x, y = (left+right-width)/2, (top+bottom-height)/2
    return tuple(round(v) for v in (x, y, x+width, y+height))


def placement_phases(beat, settings):
    """Reserve hold/move inside existing beat boundaries; never shift speech."""
    end = beat['shrink_end']
    start = beat['draw_start']
    available = end-start
    hold = settings.get('pause_seconds', .5)
    move = settings.get('move_seconds', .6)
    # Short beats retain at least half their interval for drawing.
    scale = min(1, available*.5/max(hold+move, 1e-9))
    return end-(hold+move)*scale, end-move*scale, end


def available_space(r, index, t):
    beat = r.beats[index]
    cell = index % 6
    draw_end, move_start, move_end = placement_phases(beat, r.c.get('animation', {}))
    if t >= move_end:
        return r.board(index//6, cell+1).copy()
    canvas = r.board(index//6, cell).copy()
    if t < beat['draw_start']:
        return canvas
    box = available_box(r, cell)
    if t >= move_start:
        box = lerp_box(box, r.cells[cell], smooth((t-move_start)/(move_end-move_start)))
    progress = min(1, max(0, (t-beat['draw_start'])/(draw_end-beat['draw_start'])))
    art, tip = r.reveal(index, progress)
    width, height = box[2]-box[0], box[3]-box[1]
    canvas.paste(art.resize((width,height), Image.Resampling.LANCZOS), box[:2])
    if tip is not None:
        sx, sy = width/r.fw, height/r.fh
        r.paste_hand(canvas, (box[0]+tip[0]*sx, box[1]+tip[1]*sy),
                     opacity=min(1,(1-progress)/.05), scale=min(sx,sy), motion_time=t)
    return canvas


# Legacy modes remain available. Add custom functions here to expose them in CLI.
MODES = {'available-space': available_space, 'canvas': None, 'zoom-up-draw': None}
