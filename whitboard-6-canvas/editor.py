#!/usr/bin/env python3
"""Six-cell whiteboard renderer using Pillow and FFmpeg.

python3 editor.py
python3 editor.py --mode zoom-up-draw
python3 editor.py --duration 5 --output preview_5s.mp4
python3 editor.py --validate

Requires Python 3, Pillow, ffmpeg and ffprobe. All creative choices and timing
live in config.json. Paths inside config are relative to that config file.
Raster artwork is revealed with fine ink-following brush passes, varied speed,
and wrist motion anchored at the pen tip; original pen strokes are not reconstructed. Drawing and zoom gestures use the
supplied transparent hand asset; the second gesture hand is a mirrored copy.
Default canvas mode draws directly in each cell and keeps completed drawings
visible. zoom-up-draw enables the enlarged drawing and shrink animations.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageOps

EXTENSIONS = {'.png', '.jpeg', '.jpg', '.webp'}
PHASES = ('start', 'draw_start', 'draw_end', 'shrink_start', 'shrink_end', 'slide_start', 'end')


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'json', str(path)], text=True))['format']


def resolve_image(base, name):
    path = base / name
    if path.suffix.lower() in EXTENSIONS and path.is_file():
        return path
    directory = path.parent
    matches = sorted(p for p in directory.iterdir()
                     if p.stem == path.stem and p.suffix.lower() in EXTENSIONS) if directory.is_dir() else []
    if len(matches) != 1:
        raise ValueError(f'Expected one image for {name}; found {len(matches)}. Use an explicit filename to disambiguate.')
    return matches[0]


def audio_pauses(c):
    return c['audio'].get('pauses', [])


def prepare_audio(c, base, output):
    """Insert sample-exact silence without cutting or stretching narration."""
    rate = 48000
    pauses = audio_pauses(c)
    total = round(c['audio'].get('source_duration', c['duration']) * rate)
    cuts = [0] + [round(p['source_time'] * rate) for p in pauses] + [total]
    count = len(cuts) - 1
    graph = [f'[0:a]aresample={rate},aformat=sample_fmts=s16:channel_layouts=stereo,'
             f'apad,atrim=end_sample={total},asplit={count}' +
             ''.join(f'[source{i}]' for i in range(count))]
    parts = []
    for i, (start, end) in enumerate(zip(cuts, cuts[1:])):
        graph.append(f'[source{i}]atrim=start_sample={start}:end_sample={end},'
                     f'asetpts=PTS-STARTPTS[voice{i}]')
        parts.append(f'[voice{i}]')
        if i < len(pauses):
            samples = round(pauses[i]['duration'] * rate)
            graph.append(f'anullsrc=r={rate}:cl=stereo,atrim=end_sample={samples},'
                         f'asetpts=PTS-STARTPTS[silence{i}]')
            parts.append(f'[silence{i}]')
    graph.append(''.join(parts) + f'concat=n={len(parts)}:v=0:a=1[out]')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(base / c['audio']['path']), '-filter_complex', ';'.join(graph),
                    '-map', '[out]', '-c:a', 'pcm_s16le', str(output)], check=True)


class GifAnimation:
    """Decode disposal/transparency and retain each frame's native duration."""
    def __init__(self, path, height, mirror=False, anchor=None):
        frames = []
        self.ends = []
        elapsed = 0.0
        with Image.open(path) as source:
            source_size = source.size
            for i in range(source.n_frames):
                source.seek(i)
                frames.append(source.convert('RGBA'))
                elapsed += max(10, source.info.get('duration', 100)) / 1000
                self.ends.append(elapsed)
        bounds = [frame.getbbox() for frame in frames if frame.getbbox()]
        if not bounds:
            raise ValueError(f'GIF contains no visible frames: {path}')
        crop = (min(b[0] for b in bounds), min(b[1] for b in bounds),
                max(b[2] for b in bounds), max(b[3] for b in bounds))
        self.size = (max(1, round((crop[2]-crop[0])*height/(crop[3]-crop[1]))), height)
        self.frames = []
        for frame in frames:
            frame = frame.crop(crop).resize(self.size, Image.Resampling.LANCZOS)
            self.frames.append(ImageOps.mirror(frame) if mirror else frame)
        self.duration = elapsed
        self.anchor = (0, 0)
        if anchor is not None:
            x = (anchor[0]*source_size[0]-crop[0])*self.size[0]/(crop[2]-crop[0])
            y = (anchor[1]*source_size[1]-crop[1])*self.size[1]/(crop[3]-crop[1])
            self.anchor = (self.size[0]-x if mirror else x, y)

    def frame(self, t):
        index = min(len(self.frames)-1, bisect.bisect_right(self.ends, t % self.duration))
        return self.frames[index]


def validate(c, base):
    def need(condition, message):
        if not condition:
            raise ValueError(message)
    need(c['schema_version'] == 1, 'Unsupported config schema_version')
    for program in ('ffmpeg', 'ffprobe'):
        need(shutil.which(program), f'Install {program} and put it on PATH')
    o = c['output']
    need(all(isinstance(o[k], int) and o[k] > 0 for k in ('width','height','fps')), 'Invalid output dimensions/fps')
    need(o['width'] % 2 == o['height'] % 2 == 0, 'H.264 requires even dimensions')
    need(o['width'] * 9 == o['height'] * 16, 'Output must be 16:9')
    need(o['fps'] <= 60, 'Supported frame rate is 1–60 fps')
    need(0 <= o['crf'] <= 51, 'CRF must be between 0 and 51')
    need((base / c['audio']['path']).is_file(), 'Audio file is missing')
    duration = float(probe(base / c['audio']['path'])['duration'])
    pauses = audio_pauses(c)
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
             'Each board change requires one matching silent audio pause')
        offset = 0.0
        for beat, pause in zip(slides, pauses):
            need(abs(beat['slide_start']-(pause['source_time']+offset)) < .001 and
                 abs(beat['end']-beat['slide_start']-pause['duration']) < .001,
                 'Board pull must coincide exactly with inserted silence')
            offset += pause['duration']
    return c['duration']


def smooth(p):
    p = max(0.0, min(1.0, p))
    return p*p*(3-2*p)


def lerp_box(a,b,p):
    return tuple(round(x+(y-x)*p) for x,y in zip(a,b))


class Renderer:
    def __init__(self,c,base,mode='canvas'):
        self.c,self.base=c,base
        if mode not in ('canvas','zoom-up-draw'):
            raise ValueError(f'Unknown drawing mode: {mode}')
        self.mode=mode
        self.w,self.h=c['output']['width'],c['output']['height']
        self.beats=c['beats']; self.starts=[b['start'] for b in self.beats]
        self.focus=tuple(round(x*v) for x,v in zip(c['focus']['rect'],(self.w,self.h,self.w,self.h)))
        self.fw,self.fh=self.focus[2]-self.focus[0],self.focus[3]-self.focus[1]
        m=round(self.w*c['board']['margin_fraction'])
        self.board_rect=(m,m,self.w-m,self.h-m)
        self.cw=(self.w-2*m)/3; self.ch=(self.h-2*m)/2
        self.cells=[]
        pad=round(min(self.cw,self.ch)*c['board']['cell_padding_fraction'])
        for i in range(6):
            x=m+(i%3)*self.cw; y=m+(i//3)*self.ch
            scale=min((self.cw-2*pad)/self.fw,(self.ch-2*pad)/self.fh)
            aw,ah=self.fw*scale,self.fh*scale
            left,top=x+(self.cw-aw)/2,y+(self.ch-ah)/2
            self.cells.append((round(left),round(top),round(left+aw),round(top+ah)))
        self.blank=Image.new('RGB',(self.w,self.h),c['board']['background'])
        if c['board'].get('show_guides',False):
            d=ImageDraw.Draw(self.blank); color=c['board']['line_color']; width=c['board']['line_width']
            d.rounded_rectangle(self.board_rect,radius=c['board']['corner_radius'],outline=color,width=width)
            for j in (1,2):
                x=round(m+j*self.cw); d.line((x,m,x,self.h-m),fill=color,width=width)
            d.line((m,round(m+self.ch),self.w-m,round(m+self.ch)),fill=color,width=width)
        self.hand=None
        if c['hand']['enabled']:
            with Image.open(base/c['hand']['path']) as im:
                raw=ImageOps.exif_transpose(im).convert('RGBA')
            hh=round(self.h*c['hand']['height_fraction'])
            self.hand=raw.resize((round(raw.width*hh/raw.height),hh),Image.Resampling.LANCZOS)
            self.tip=(c['hand']['tip'][0]*self.hand.width,c['hand']['tip'][1]*self.hand.height)
            self.mirrored=ImageOps.mirror(self.hand)
        # Uniform arc-length path. Row spacing <= brush width guarantees coverage.
        self.brush=max(8,round(self.fh*c['reveal']['brush_fraction']))
        rows=max(2,math.ceil(self.fh/(self.brush*c['reveal']['row_spacing']))+1)
        self.points=[]
        for row in range(rows):
            y=row*(self.fh-1)/(rows-1)
            xs=(0,self.fw-1) if row%2==0 else (self.fw-1,0)
            self.points.extend([(xs[0],y),(xs[1],y)])
        self.lengths=[0.0]
        for a,b in zip(self.points,self.points[1:]): self.lengths.append(self.lengths[-1]+math.dist(a,b))
        self.watching = self.flying = None
        bird = c.get('jackdaw', {})
        if bird.get('enabled', False):
            self.watching = GifAnimation(base / bird['watching_path'],
                                        round(self.h*bird['watching_height_fraction']))
            self.flying = GifAnimation(base / bird['flying_path'],
                                      round(self.h*bird['flying_height_fraction']),
                                      mirror=True, anchor=bird['beak'])

    @lru_cache(maxsize=8)
    def asset(self,index):
        with Image.open(resolve_image(self.base,self.beats[index]['image'])) as im:
            raw=ImageOps.exif_transpose(im).convert('RGBA')
        settings=self.c.get('artwork',{})
        if settings.get('trim_white_margins',False):
            flat=Image.new('RGB',raw.size,'white'); flat.paste(raw,(0,0),raw)
            difference=ImageChops.difference(flat,Image.new('RGB',raw.size,'white')).convert('L')
            threshold=255-settings.get('white_threshold',245)
            bounds=difference.point(lambda v:255 if v>threshold else 0).getbbox()
            if bounds:
                x0,y0,x1,y1=bounds
                pad=round(max(x1-x0,y1-y0)*settings.get('padding_fraction',.04))
                raw=raw.crop((max(0,x0-pad),max(0,y0-pad),min(raw.width,x1+pad),min(raw.height,y1+pad)))
        fitted=ImageOps.contain(raw,(self.fw,self.fh),Image.Resampling.LANCZOS)
        layer=Image.new('RGB',(self.fw,self.fh),self.c['board']['background'])
        layer.paste(fitted,((self.fw-fitted.width)//2,(self.fh-fitted.height)//2),fitted)
        return layer

    @lru_cache(maxsize=12)
    def thumbnail(self,index):
        box=self.cells[index%6]
        return self.asset(index).resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)

    @lru_cache(maxsize=8)
    def board(self,board_index,completed):
        canvas=self.blank.copy()
        for cell in range(completed):
            index=board_index*6+cell
            canvas.paste(self.thumbnail(index),self.cells[cell][:2])
        return canvas

    @lru_cache(maxsize=8)
    def drawing_path(self,index):
        # Follow separate ink spans with short, uneven strokes. Travel between
        # spans is a fast pen lift, so blank gaps do not consume drawing time.
        ink=ImageChops.difference(self.asset(index),Image.new('RGB',(self.fw,self.fh),'white')).convert('L')
        ink=ink.point(lambda v:255 if v>self.c['reveal'].get('ink_threshold',20) else 0)
        points=[]; drawing=[]
        step=max(1,round(self.brush*self.c['reveal']['row_spacing']))
        for row,y in enumerate(range(0,self.fh+step,step)):
            y=min(y,self.fh-1)
            top=max(0,round(y-step/2)); bottom=min(self.fh,round(y+step/2)+1)
            strip=ink.crop((0,top,self.fw,bottom))
            # Collapse each column to detect disconnected details and lettering.
            columns=strip.resize((self.fw,1),Image.Resampling.BOX)
            occupied=[x for x,v in enumerate(columns.getdata()) if v]
            if not occupied: continue
            spans=[]; left=previous=occupied[0]
            for x in occupied[1:]:
                if x-previous>self.brush*.7:
                    spans.append((max(0,left-2),min(self.fw-1,previous+2)))
                    left=x
                previous=x
            spans.append((max(0,left-2),min(self.fw-1,previous+2)))
            if row%2: spans.reverse()
            for left,right in spans:
                if row%2: left,right=right,left
                count=max(2,math.ceil(abs(right-left)/max(4,self.brush*.6)))
                for j in range(count+1):
                    x=left+(right-left)*j/count
                    wobble=self.brush*.10*math.sin(x*.11+row*1.7+index)
                    points.append((x,max(0,min(self.fh-1,y+wobble))))
                    drawing.append(j>0)
        if len(points)<2:
            return self.points,self.lengths,[False]+[True]*(len(self.points)-1)
        lengths=[0.0]
        for n,(a,b) in enumerate(zip(points,points[1:]),1):
            # Pen lifts are quicker; short changes in pressure/speed are stable
            # across renders and independent of frame rate.
            speed=(1+.22*math.sin(n*.73+index)) if drawing[n] else 3.5
            lengths.append(lengths[-1]+max(.001,math.dist(a,b)/speed))
        return points,lengths,drawing

    def reveal(self,index,p):
        if p>=1: return self.asset(index),None
        points,lengths,drawing=self.drawing_path(index)
        p=max(0,p)
        progress=p+.010*math.sin(14*math.pi*p)+.003*math.sin(30*math.pi*p)
        distance=progress*lengths[-1]
        k=min(len(points)-2,max(0,bisect.bisect_right(lengths,distance)-1))
        a,b=points[k:k+2]
        f=(distance-lengths[k])/max(1e-9,lengths[k+1]-lengths[k])
        tip=(a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)
        mask=Image.new('L',(self.fw,self.fh)); d=ImageDraw.Draw(mask)
        r=self.brush/2
        for n in range(1,k+2):
            if not drawing[n]: continue
            end=tip if n==k+1 else points[n]
            d.line((points[n-1],end),fill=255,width=self.brush)
            for x,y in (points[n-1],end):
                d.ellipse((x-r,y-r,x+r,y+r),fill=255)
        image=Image.new('RGB',(self.fw,self.fh),self.c['board']['background'])
        image.paste(self.asset(index),(0,0),mask)
        return image,tip

    @lru_cache(maxsize=128)
    def hand_variant(self,mirror,scale,angle=0):
        hand=self.mirrored if mirror else self.hand
        tip=(hand.width-self.tip[0],self.tip[1]) if mirror else self.tip
        if scale!=1:
            hand=hand.resize((max(1,round(hand.width*scale)),max(1,round(hand.height*scale))),Image.Resampling.LANCZOS)
            tip=(tip[0]*scale,tip[1]*scale)
        if angle:
            old_center=(hand.width/2,hand.height/2)
            hand=hand.rotate(angle,Image.Resampling.BICUBIC,expand=True)
            dx,dy=tip[0]-old_center[0],tip[1]-old_center[1]
            radians=math.radians(angle)
            tip=(hand.width/2+math.cos(radians)*dx+math.sin(radians)*dy,
                 hand.height/2-math.sin(radians)*dx+math.cos(radians)*dy)
        return hand,tip

    def paste_hand(self,canvas,point,mirror=False,opacity=1,scale=1,motion_time=None):
        if self.hand is None or opacity<=0: return
        angle=0
        if motion_time is not None:
            strength=self.c['hand'].get('wrist_sway_degrees',5.0)
            angle=round(2*strength*(.65*math.sin(motion_time*13.7)+
                                    .25*math.sin(motion_time*29.3)+
                                    .10*math.sin(motion_time*5.1)))/2
        hand,tip=self.hand_variant(mirror,scale,angle)
        if opacity<1:
            hand=hand.copy(); hand.putalpha(hand.getchannel('A').point(lambda a:round(a*opacity)))
        canvas.paste(hand,(round(point[0]-tip[0]),round(point[1]-tip[1])),hand)

    def gestures(self,canvas,box,p):
        if not self.c['hand']['zoom_gesture']: return
        opacity=math.sin(math.pi*max(0,min(1,p)))*.9
        y=box[1]+(box[3]-box[1])*.60
        self.paste_hand(canvas,(box[0]+12,y),True,opacity)
        self.paste_hand(canvas,(box[2]-12,y),False,opacity)

    def paste_watcher(self, canvas, t):
        bird = self.watching.frame(t)
        margin = round(self.w*.008)
        canvas.paste(bird, (self.w-bird.width-margin, round(self.h*.01)), bird)

    def pull_board(self, index, t):
        beat = self.beats[index]
        elapsed = t-beat['slide_start']
        phase = elapsed/(beat['end']-beat['slide_start'])
        # Reserve the last part for releasing the paper and flying off screen.
        amount = smooth(phase/.86)
        offset = round(amount*self.w)
        edge = self.w-offset
        canvas = self.blank.copy()
        canvas.paste(self.board(index//6, 6), (-offset, 0))
        canvas.paste(self.blank, (edge, 0))
        draw = ImageDraw.Draw(canvas)
        if edge > 0:
            # A temporary page edge makes the white-on-white pull readable.
            for n in range(7, 0, -1):
                shade = 225+4*n
                draw.line((edge-n, 0, edge-n, self.h), fill=(shade,)*3)
            draw.line((edge, 0, edge, self.h), fill='#c8c8c8', width=2)
        release = smooth((phase-.86)/.14)
        mouth = (edge-self.w*.013-release*(self.flying.size[0]+self.w*.025),
                 self.h*.145+math.sin(elapsed*19)*self.h*.003)
        if phase < .86:
            # The beak grips this folded paper tab. It moves with the new page.
            draw.polygon([(edge+2, mouth[1]-12), (mouth[0], mouth[1]),
                          (edge+2, mouth[1]+12)], fill='#ffffff', outline='#7c7c7c')
        bird = self.flying.frame(elapsed)
        x,y = self.flying.anchor
        canvas.paste(bird, (round(mouth[0]-x), round(mouth[1]-y)), bird)
        return canvas

    def frame(self, t):
        index = min(len(self.beats)-1, max(0,bisect.bisect_right(self.starts,t)-1))
        beat = self.beats[index]
        if self.flying is not None and beat['slide_start'] <= t < beat['end']:
            return self.pull_board(index, t)
        canvas = self.drawing_frame(t)
        if self.watching is not None:
            self.paste_watcher(canvas, t)
        return canvas

    def drawing_frame(self,t):
        i=min(len(self.beats)-1,max(0,bisect.bisect_right(self.starts,t)-1))
        b=self.beats[i]; cell=i%6; board=i//6
        if t>=b['slide_start'] and b['slide_start']<b['end']:
            p=smooth((t-b['slide_start'])/(b['end']-b['slide_start']))
            x=round(p*self.w)
            canvas=Image.new('RGB',(self.w,self.h),self.c['board']['background'])
            canvas.paste(self.board(board,6),(-x,0)); canvas.paste(self.blank,(self.w-x,0))
            return canvas
        if t>=b['shrink_end']:
            return self.board(board,cell+1).copy()
        base=self.board(board,cell)
        if self.mode=='canvas':
            # Reuse the former zoom/shrink time for drawing, retaining the final
            # board hold and slide timings so narration remains synchronized.
            p=max(0,min(1,(t-b['start'])/(b['shrink_end']-b['start'])))
            art,tip=self.reveal(i,p)
            box=self.cells[cell]; width,height=box[2]-box[0],box[3]-box[1]
            canvas=base.copy()
            canvas.paste(art.resize((width,height),Image.Resampling.LANCZOS),box[:2])
            if tip is not None:
                sx,sy=width/self.fw,height/self.fh
                point=(box[0]+tip[0]*sx,box[1]+tip[1]*sy)
                self.paste_hand(canvas,point,opacity=min(1,max(0,(1-p)/.05)),scale=min(sx,sy),motion_time=t)
            return canvas
        if t<b['draw_start']:
            phase=(t-b['start'])/(b['draw_start']-b['start'])
            amount=smooth(phase); box=lerp_box(self.cells[cell],self.focus,amount)
            canvas=Image.blend(base,Image.new('RGB',base.size,self.c['board']['background']),amount)
            self.gestures(canvas,box,phase)
            return canvas
        if t>=b['shrink_start']:
            phase=(t-b['shrink_start'])/(b['shrink_end']-b['shrink_start'])
            amount=1-smooth(phase); box=lerp_box(self.cells[cell],self.focus,amount)
            canvas=Image.blend(base,Image.new('RGB',base.size,self.c['board']['background']),amount)
            art=self.asset(i).resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.BICUBIC)
            canvas.paste(art,box[:2]); self.gestures(canvas,box,phase)
            return canvas
        p=(t-b['draw_start'])/(b['draw_end']-b['draw_start'])
        art,tip=self.reveal(i,p)
        canvas=Image.new('RGB',(self.w,self.h),self.c['board']['background'])
        canvas.paste(art,self.focus[:2])
        if tip is not None:
            fade=min(1,max(0,(1-p)/.05))
            self.paste_hand(canvas,(self.focus[0]+tip[0],self.focus[1]+tip[1]),opacity=fade,motion_time=t)
        return canvas


def render(c,base,args):
    if audio_pauses(c):
        with tempfile.TemporaryDirectory(prefix='whiteboard-audio-') as directory:
            audio_path = Path(directory) / 'narration_with_pauses.wav'
            prepare_audio(c, base, audio_path)
            render_frames(c, base, args, audio_path)
    else:
        render_frames(c, base, args, base/c['audio']['path'])


def render_frames(c,base,args,audio_path):
    start=args.start
    if not 0<=start<c['duration']: raise ValueError('--start is outside the timeline')
    duration=min(c['duration']-start,args.duration if args.duration is not None else c['duration'])
    if duration<=0: raise ValueError('--duration must be positive')
    output=Path(args.output).expanduser().resolve() if args.output else base/c['output']['path']
    if output.suffix.lower()!='.mp4': raise ValueError('Use an .mp4 output filename')
    if output.exists() and not args.overwrite: raise ValueError(f'{output} already exists; use --overwrite to replace it')
    output.parent.mkdir(parents=True,exist_ok=True)
    renderer=Renderer(c,base,args.mode)
    o=c['output']; fps=o['fps']; frames=math.ceil(duration*fps-1e-9)
    with tempfile.NamedTemporaryFile(prefix='.whiteboard-',suffix='.mp4',dir=output.parent,delete=False) as f: temporary=Path(f.name)
    command=['ffmpeg','-hide_banner','-loglevel','warning','-y',
        '-f','rawvideo','-pixel_format','rgb24','-video_size',f'{o["width"]}x{o["height"]}',
        '-framerate',str(fps),'-i','pipe:0','-ss',str(start),'-i',str(audio_path),
        '-map','0:v:0','-map','1:a:0','-t',f'{duration:.6f}',
        '-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p',
        '-c:v','libx264','-preset',o['preset'],'-crf',str(o['crf']),
        '-profile:v','high','-level:v','4.2','-g',str(fps*2),'-pix_fmt','yuv420p',
        '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
        '-c:a','aac','-b:a',o['audio_bitrate'],'-ar','48000','-ac','2',
        '-movflags','+faststart',str(temporary)]
    proc=None
    try:
        with tempfile.TemporaryFile() as log:
            proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
            began=time.monotonic(); reported=began
            try:
                for n in range(frames):
                    proc.stdin.write(renderer.frame(start+n/fps).tobytes())
                    now=time.monotonic()
                    if now-reported>=5:
                        print(f'{n+1}/{frames} frames ({100*(n+1)/frames:.1f}%), {(n+1)/(now-began):.1f} fps',flush=True)
                        reported=now
                proc.stdin.close()
                code=proc.wait()
            except BrokenPipeError:
                code=proc.wait()
            if code:
                log.seek(0); raise RuntimeError('FFmpeg failed:\n'+log.read().decode(errors='replace'))
        temporary.replace(output)
        print(f'Saved {output} ({duration:.3f} seconds, {o["width"]}x{o["height"]}, {fps} fps)')
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        temporary.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config',type=Path,default=Path(__file__).resolve().with_name('config.json'))
    parser.add_argument('--mode',choices=('canvas','zoom-up-draw'),default='canvas',
                        help='canvas: draw in place (default); zoom-up-draw: enlarge, draw, then shrink')
    parser.add_argument('--validate',action='store_true',help='Check config and asset names without rendering')
    parser.add_argument('--duration',type=float,help='Render only this many seconds')
    parser.add_argument('--start',type=float,default=0,help='Preview start time in seconds')
    parser.add_argument('--output',help='Output MP4 path; relative to current directory')
    parser.add_argument('--overwrite',action='store_true',help='Replace an existing output after successful rendering')
    args=parser.parse_args()
    try:
        config_path=args.config.expanduser().resolve(); base=config_path.parent
        c=json.loads(config_path.read_text()); validate(c,base)
        print(f'Validated {len(c["beats"])} images across {len(c["beats"])//6} boards; duration {c["duration"]:.3f}s',flush=True)
        if not args.validate: render(c,base,args)
        return 0
    except KeyboardInterrupt:
        print('Cancelled; incomplete temporary output removed.',file=sys.stderr); return 130
    except (ValueError,KeyError,OSError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f'Error: {exc}',file=sys.stderr); return 1


if __name__=='__main__':
    raise SystemExit(main())
