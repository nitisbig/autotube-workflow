#!/usr/bin/env python3
"""Reusable whiteboard renderer. Requires Python 3, Pillow, ffmpeg and ffprobe.

  python3 editor.py                         # CPU, single-pass H.264
  python3 editor.py --fps 30 gpu --true      # NVIDIA NVENC VBR multipass
  python3 editor.py --gpu true              # equivalent GPU syntax
  python3 editor.py --background black      # optional background behind artwork
  python3 editor.py --background none       # transparent ProRes 4444 MOV
  python3 editor.py --validate              # check inputs; do not render

All project choices live in edits.json. Times are absolute seconds. Section rects
are normalized image coordinates. Camera x values are measured in screen widths.
Hand tip is a normalized coordinate in the ORIGINAL hand PNG, before scaling.
The reveal is a continuous serpentine brush erasing a white cover, not AI stroke
reconstruction. No frames or intermediate video are stored during export.
The artwork, white reveal mask, and hand are the three drawing layers. The
background is optional and may be set in canvas.background or --background.
NVENC fullres multipass is hardware frame-level analysis, not x264's two complete
video passes. GPU mode accelerates encoding; Pillow composition remains on CPU.
"""
import argparse
import bisect
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from functools import lru_cache
from collections import OrderedDict
from PIL import Image, ImageDraw, ImageOps


def probe(path):
    return float(json.loads(
        subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of', 'json', str(path)], text=True))['format']['duration'])


def validate(c, base):
    def require(ok, msg):
        if not ok:
            raise ValueError(msg)
    require(c['schema_version'] == 1, 'Unsupported schema_version')
    require(c['canvas']['fit'] == 'contain', 'Only contain image fit is supported')
    require(c['reveal']['pattern'] == 'serpentine', 'Only serpentine reveal is supported')
    require(c['camera']['easing'] in ('smoothstep', 'linear'), 'Unsupported camera easing')
    require(c['hand']['height_fraction'] > 0 and len(c['hand']['tip']) == 2
            and all(0 <= v <= 1 for v in c['hand']['tip']), 'Invalid hand size or tip')
    require(len(c['scenes']) > 0, 'At least one image is required')
    for exe in ('ffmpeg', 'ffprobe'):
        require(shutil.which(exe), f'{exe} is required on PATH')
    w, h = c['output']['width'], c['output']['height']
    require(w > 0 and h > 0 and w % 2 == h % 2 == 0 and w * 9 == h * 16,
            'Output must be positive even dimensions in 16:9')
    require(0 < c['output']['fps'] <= 120, 'Invalid fps')
    inputs = [c['audio']['path'], c['sources']['subtitles']]
    if c['hand']['enabled']:
        inputs.append(c['hand']['path'])
    for p in inputs:
        require((base / p).is_file(), f'Missing input: {p}')
    duration = probe(base / c['audio']['path'])
    require(abs(duration - c['output']['duration']) < .15, 'Audio duration differs from configured timeline')
    require(c['reveal']['brush_width_fraction'] > 0, 'Brush width must be positive')
    require(0 < c['reveal']['row_spacing_fraction'] <= 1, 'Row spacing must be in (0,1]')
    previous = -1
    for scene in c['scenes']:
        require((base / scene['image']).is_file(), f"Missing {scene['image']}")
        require(len(scene['sections']) == 4, 'Each image needs four sections')
        for s in scene['sections']:
            require(previous <= s['start'] < s['draw_end'] <= s['end'] <= duration,
                    f"Invalid timing: {scene['image']} section {s['id']}")
            previous = s['end']
            x0, y0, x1, y1 = s['rect']
            require(0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, 'Invalid section rect')
    keys = c['camera']['keyframes']
    require(keys[0]['time'] == 0, 'Camera must start at zero')
    require(all(a['time'] < b['time'] and a['x'] <= b['x'] for a,b in zip(keys, keys[1:])),
            'Camera keys must increase in time and position')
    require(keys[-1]['time'] <= duration, 'Camera extends beyond audio')
    return duration


class Renderer:
    def __init__(self, c, base):
        self.c, self.base = c, base
        self.w, self.h = c['output']['width'], c['output']['height']
        self.bg = c['canvas'].get('background')
        self.transparent = self.bg == 'none'
        self.mode = 'RGBA' if self.transparent else 'RGB'
        self.fill = (0, 0, 0, 0) if self.transparent else (self.bg or 'white')
        self.mask_fill = 'white'
        self.hand = None
        if c['hand']['enabled']:
            with Image.open(base / c['hand']['path']) as source:
                raw = source.convert('RGBA')
            scale = self.h * c['hand']['height_fraction'] / raw.height
            self.hand = raw.resize((round(raw.width * scale), round(raw.height * scale)), Image.Resampling.LANCZOS)
            self.tip = (c['hand']['tip'][0] * self.hand.width, c['hand']['tip'][1] * self.hand.height)
        self.keys = c['camera']['keyframes']
        self.times = [k['time'] for k in self.keys]
        self.boards = OrderedDict()

    @lru_cache(maxsize=3)
    def asset(self, index):
        with Image.open(self.base / self.c['scenes'][index]['image']) as source:
            raw = ImageOps.exif_transpose(source).convert('RGBA')
        fitted = ImageOps.contain(raw, (self.w, self.h), Image.Resampling.LANCZOS)
        if self.transparent:
            im = fitted
        else:
            im = Image.new('RGB', fitted.size, self.bg or 'white')
            im.paste(fitted, (0, 0), fitted)
        return im, (round((self.w-im.width)/2), round((self.h-im.height)/2))

    @lru_cache(maxsize=12)
    def geometry(self, index, section):
        im, _ = self.asset(index)
        s = self.c['scenes'][index]['sections'][section]
        a,b,c,d = s['rect']
        box = (round(a*im.width), round(b*im.height), round(c*im.width), round(d*im.height))
        width, height = box[2]-box[0], box[3]-box[1]
        brush = max(4, round(self.w*self.c['reveal']['brush_width_fraction']))
        step = max(1, brush*self.c['reveal']['row_spacing_fraction'])
        rows = max(2, math.ceil(height/step)+1)
        points = []
        for row in range(rows):
            y = row*(height-1)/(rows-1)
            xs = (0, width-1) if row % 2 == 0 else (width-1, 0)
            points.extend([(xs[0], y), (xs[1], y)])
        lengths = [0.0]
        for p,q in zip(points,points[1:]):
            lengths.append(lengths[-1]+math.dist(p,q))
        return box, brush, points, lengths, im.crop(box)

    def revealed(self, index, time):
        im, offset = self.asset(index)
        state = self.boards.get(index)
        if state is None or time < state['time']:
            state = {'board': Image.new(self.mode, im.size, self.mask_fill),
                     'completed': -1, 'time': -float('inf')}
            self.boards[index] = state
            if len(self.boards) > 3:
                self.boards.popitem(last=False)
        else:
            self.boards.move_to_end(index)
        state['time'] = time
        board = state['board']
        tip = None
        overlay = None
        for j,s in enumerate(self.c['scenes'][index]['sections']):
            box, brush, points, lengths, crop = self.geometry(index,j)
            if time < s['start']:
                continue
            if time >= s['draw_end']:
                if j > state['completed']:
                    board.paste(crop, box[:2])
                    state['completed'] = j
                continue
            if self.transparent and board is state['board']:
                board = board.copy()
            progress = max(0, min(1, (time-s['start'])/(s['draw_end']-s['start'])))
            distance = progress*lengths[-1]
            k = min(len(points)-2, max(0,bisect.bisect_right(lengths,distance)-1))
            fraction = (distance-lengths[k])/(lengths[k+1]-lengths[k])
            p,q = points[k],points[k+1]
            end = (p[0]+(q[0]-p[0])*fraction, p[1]+(q[1]-p[1])*fraction)
            mask = Image.new('L', crop.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.line(points[:k+1]+[end], fill=255, width=brush, joint='curve')
            r = brush/2
            for x,y in points[:k+1]+[end]:
                draw.ellipse((x-r,y-r,x+r,y+r),fill=255)
            if self.transparent:
                board.paste(crop,box[:2],mask)
            else:
                overlay = (crop, mask, box)
            tip = (offset[0]+box[0]+end[0],offset[1]+box[1]+end[1])
        return board, offset, tip, overlay

    def camera(self, time):
        i = max(0,bisect.bisect_right(self.times,time)-1)
        if i == len(self.keys)-1:
            return self.keys[i]['x']*self.w
        a,b = self.keys[i:i+2]
        p = (time-a['time'])/(b['time']-a['time'])
        if self.c['camera']['easing'] == 'smoothstep':
            p = p*p*(3-2*p)
        return (a['x']+(b['x']-a['x'])*p)*self.w

    def frame(self, time):
        canvas = Image.new(self.mode,(self.w,self.h),self.fill)
        cam = self.camera(time)
        hand_at = None
        first = max(0,math.floor(cam/self.w))
        for index in range(first,min(first+2,len(self.c['scenes']))):
            board,offset,tip,overlay = self.revealed(index,time)
            x = round(index*self.w-cam)
            if self.transparent:
                canvas.alpha_composite(board,(x+offset[0],offset[1]))
            else:
                canvas.paste(board,(x+offset[0],offset[1]))
                if overlay is not None:
                    crop, mask, box = overlay
                    canvas.paste(crop,(x+offset[0]+box[0],offset[1]+box[1]),mask)
            if tip is not None and self.hand is not None:
                hand_at = (round(x+tip[0]-self.tip[0]),round(tip[1]-self.tip[1]))
        if hand_at is not None and self.hand is not None:
            if self.transparent:
                canvas.alpha_composite(self.hand,hand_at)
            else:
                canvas.paste(self.hand,hand_at,self.hand)
        return canvas


def command(c, base, gpu, pass_no, log, target):
    o = c['output']
    transparent = c['canvas'].get('background') == 'none'
    cmd = ['ffmpeg','-hide_banner','-y','-loglevel','warning']
    if gpu == 'vaapi':
        cmd += ['-vaapi_device', o.get('gpu_device', '/dev/dri/renderD128')]
    cmd += ['-f','rawvideo',
           '-pixel_format','rgba' if transparent else 'rgb24',
           '-video_size',f"{o['width']}x{o['height']}",
           '-framerate',str(o['fps']),'-i','pipe:0']
    if pass_no != 1:
        cmd += ['-i',str(base/c['audio']['path']),'-map','0:v:0','-map','1:a:0']
    if transparent:
        return cmd + ['-c:v','prores_ks','-profile:v','4444','-pix_fmt','yuva444p10le',
                      '-alpha_bits','16','-vf','setsar=1,setfield=prog',
                      '-c:a','aac','-b:a',c['audio']['bitrate'],
                      '-ar',str(c['audio']['sample_rate']),'-t',str(o['duration']),str(target)]
    cmd += ['-c:v', 'h264_nvenc' if gpu == 'nvenc' else 'h264_vaapi' if gpu == 'vaapi' else 'libx264',
            '-profile:v','high','-g',str(round(o['fps']*o['keyframe_seconds']))]
    if gpu == 'nvenc':
        cmd += ['-pix_fmt','yuv420p','-b:v',o['bitrate'],'-maxrate',o['maxrate'],
                '-bufsize',o['bufsize'],'-vf','setsar=1,setfield=prog',
                '-preset',o['nvenc_preset'],'-rc','vbr','-multipass','fullres']
    elif gpu == 'vaapi':
        cmd += ['-vf','setsar=1,setfield=prog,format=nv12,hwupload',
                '-rc_mode','CQP','-qp',str(o.get('gpu_qp',18))]
    else:
        cmd += ['-pix_fmt','yuv420p','-vf','setsar=1,setfield=prog',
                '-preset',o.get('cpu_preset','veryfast')]
        if o.get('two_pass',False):
            cmd += ['-b:v',o['bitrate'],'-maxrate',o['maxrate'],
                    '-bufsize',o['bufsize'],'-pass',str(pass_no),'-passlogfile',str(log)]
        else:
            cmd += ['-crf',str(o.get('crf',18)),'-maxrate',o['maxrate'],
                    '-bufsize',o['bufsize']]
    if pass_no == 1:
        return cmd+['-an','-f','null',os.devnull]
    return cmd+['-c:a','aac','-b:a',c['audio']['bitrate'],'-ar',str(c['audio']['sample_rate']),
                '-t',str(o['duration']),'-movflags','+faststart',str(target)]


def select_gpu(c, requested):
    """Test the actual encoder, driver and device before starting a long render."""
    if not requested:
        return None
    o = c['output']
    check = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
             '-i', f"color=white:s={o['width']}x{o['height']}:r={o['fps']}",
             '-c:v', 'h264_nvenc', '-preset', o['nvenc_preset'],
             '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-rc', 'vbr',
             '-multipass', 'fullres', '-b:v', o['bitrate'],
             '-maxrate', o['maxrate'], '-bufsize', o['bufsize'],
             '-frames:v', '2', '-f', 'null', '-']
    try:
        result = subprocess.run(check, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return 'nvenc'
        detail = result.stderr.strip()
        if 'libcuda.so.1' in detail:
            reason = 'NVIDIA CUDA driver library libcuda.so.1 is unavailable.'
        else:
            reason = next((line for line in detail.splitlines() if line.strip()),
                          'NVIDIA encoder initialization failed.')
    except subprocess.TimeoutExpired:
        reason = 'NVIDIA encoder availability check timed out.'
    device = Path(o.get('gpu_device', '/dev/dri/renderD128'))
    if device.exists():
        vaapi_check = ['ffmpeg','-hide_banner','-loglevel','error','-vaapi_device',str(device),
                       '-f','lavfi','-i','color=white:s=128x128:r=1',
                       '-vf','format=nv12,hwupload','-c:v','h264_vaapi',
                       '-frames:v','1','-f','null','-']
        try:
            if subprocess.run(vaapi_check, capture_output=True, timeout=30).returncode == 0:
                return 'vaapi'
        except subprocess.TimeoutExpired:
            pass
    if not o.get('gpu_fallback_to_cpu', True):
        raise RuntimeError(reason + ' Enable output.gpu_fallback_to_cpu or use --gpu false.')
    print(f'{reason}\nNo working GPU encoder found; using CPU libx264 '
          f"{'two-pass' if o.get('two_pass',False) else 'single-pass'} instead.", flush=True)
    return None


def clock_text(seconds):
    if seconds is None:
        return 'estimating'
    seconds = max(0, round(seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'


class Progress:
    """Wall-clock ETA across all passes; includes encoder drain in elapsed time."""
    def __init__(self, frames, passes, interval=2):
        self.frames, self.passes = frames, passes
        self.interval = max(.2, float(interval))
        self.started = time.monotonic()
        self.last = -float('inf')

    def update(self, pass_index, frames_done, stage='rendering', force=False):
        now = time.monotonic()
        if not force and now - self.last < self.interval:
            return
        self.last = now
        elapsed = now - self.started
        done = pass_index * self.frames + frames_done
        total = self.frames * self.passes
        fraction = done / total
        remaining = elapsed * (total-done) / done if done and elapsed >= 2 else None
        if done == total:
            remaining = None  # FFmpeg still needs to flush and mux the file.
        percent = min(99.9, fraction * 100)
        print(f'Overall {percent:5.1f}% | Pass {pass_index+1}/{self.passes} '
              f'{frames_done/self.frames:5.1%} | Elapsed {clock_text(elapsed)} | '
              f'Left ~{clock_text(remaining)} | '
              f'Total ~{clock_text(elapsed+remaining if remaining is not None else None)} | '
              f'{stage}', flush=True)

    def finish(self):
        print(f'Overall 100.0% | Elapsed {clock_text(time.monotonic()-self.started)} | '
              'Left 00:00:00 | Complete', flush=True)


def export(c, base, gpu):
    destination = base/c['output']['path']
    transparent = c['canvas'].get('background') == 'none'
    if transparent and destination.suffix.lower() == '.mp4':
        destination = destination.with_suffix('.mov')
    if destination.suffix.lower() != ('.mov' if transparent else '.mp4'):
        raise ValueError('Output path must use .mov for no background or .mp4 otherwise')
    if destination.exists() and not c['output']['overwrite']:
        raise ValueError(f'{destination} exists; set output.overwrite to true to replace it')
    destination.parent.mkdir(parents=True,exist_ok=True)
    gpu = None if transparent else select_gpu(c, gpu)
    passes = [1, 2] if not transparent and not gpu and c['output'].get('two_pass',False) else [2]
    encoder = ('CPU ProRes 4444 with alpha' if transparent else
               'NVIDIA NVENC VBR multipass' if gpu == 'nvenc' else
               'VAAPI H.264' if gpu == 'vaapi' else
               f"CPU libx264 {'VBR two-pass' if c['output'].get('two_pass',False) else 'single-pass CRF'}")
    print('Encoder: ' + encoder, flush=True)
    count = math.ceil(c['output']['duration']*c['output']['fps'])
    progress = Progress(count, len(passes), c['output'].get('progress_interval_seconds', 2))
    with tempfile.TemporaryDirectory(prefix='.editor-',dir=destination.parent) as temp:
        target = Path(temp)/('output.mov' if transparent else 'output.mp4')
        for pass_index, pass_no in enumerate(passes):
            progress.update(pass_index, 0, force=True)
            renderer = Renderer(c,base)
            cmd = command(c,base,gpu,pass_no,Path(temp)/'pass',target)
            proc = subprocess.Popen(cmd,stdin=subprocess.PIPE)
            try:
                for n in range(count):
                    proc.stdin.write(renderer.frame(n/c['output']['fps']).tobytes())
                    progress.update(pass_index, n+1)
                proc.stdin.close()
                while proc.poll() is None:
                    progress.update(pass_index, count, stage='finishing encoder / muxing')
                    time.sleep(.2)
                if proc.returncode:
                    raise RuntimeError('FFmpeg encoding failed; see diagnostics above')
            except BaseException:
                proc.kill()
                proc.wait()
                raise
        os.replace(target,destination)
    progress.finish()
    print(f'Created {destination}')


def main():
    parser = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config',type=Path,default=Path(__file__).with_name('edits.json'))
    parser.add_argument('--fps',type=float)
    parser.add_argument('--background',choices=['none','white','black'],
                        help='override canvas background; none writes a transparent .mov')
    parser.add_argument('--gpu',choices=['true','false'])
    parser.add_argument('mode',nargs='?',choices=['gpu'])
    parser.add_argument('--true',action='store_true',dest='gpu_true')
    parser.add_argument('--validate',action='store_true')
    args = parser.parse_args()
    config = args.config.resolve()
    c = json.loads(config.read_text())
    if args.fps is not None:
        c['output']['fps'] = args.fps
    if args.background is not None:
        c['canvas']['background'] = args.background
    gpu = c['output']['gpu']
    if args.gpu is not None:
        gpu = args.gpu == 'true'
    if args.mode == 'gpu' or args.gpu_true:
        gpu = True
    validate(c,config.parent)
    if args.validate:
        print(f"Valid: {len(c['scenes'])} images, {sum(len(s['sections']) for s in c['scenes'])} sections, "
              f"{c['output']['duration']:.3f}s, {c['output']['fps']} fps; GPU={gpu}. No video rendered.")
        return
    export(c,config.parent,gpu)


if __name__ == '__main__':
    try:
        main()
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError,RuntimeError) as exc:
        sys.exit(f'Error: {exc}')
