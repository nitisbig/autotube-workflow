#!/usr/bin/env python3
"""Local, declarative Manim renderer. Run: python3 editor.py --help."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys


def read_srt(path):
    cues = {}
    for block in re.split(r'\n\s*\n', Path(path).read_text(encoding='utf-8-sig').strip()):
        lines = block.splitlines()
        if len(lines) < 3:
            raise ValueError('Malformed SRT block: ' + block)
        def seconds(s):
            h, m, sec = s.replace(',', '.').split(':')
            return int(h)*3600 + int(m)*60 + float(sec)
        start, end = map(seconds, lines[1].split(' --> '))
        if end <= start or int(lines[0]) in cues:
            raise ValueError('Invalid or duplicate subtitle cue')
        cues[int(lines[0])] = dict(start=start, end=end, text=' '.join(lines[2:]))
    return cues


def resolve(value, cues):
    if isinstance(value, (float, int)):
        return float(value)
    return cues[value['cue']][value.get('edge', 'start')] + value.get('offset', 0)


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def prepare(path, mode=None, duration=None, fps=None):
    path = Path(path).resolve()
    cfg = json.loads(path.read_text())
    if cfg.get('version') != 1:
        raise ValueError('Expected config version 1')
    cfg['mode'] = mode or cfg.get('mode', 'basic')
    if cfg['mode'] not in ('basic', 'advanced'):
        raise ValueError('mode must be basic or advanced')
    for key in ('audio', 'subtitles'):
        cfg[key] = str((path.parent / cfg[key]).resolve())
        if not Path(cfg[key]).is_file():
            raise ValueError('Missing ' + cfg[key])
    cues = read_srt(cfg['subtitles'])
    audio_duration = float(probe(cfg['audio'])['format']['duration'])
    cfg['duration'] = min(duration, audio_duration) if duration is not None else audio_duration
    if cfg['duration'] <= 0:
        raise ValueError('Duration must be positive')
    export = cfg.setdefault('export', {})
    for k, v in dict(width=1920, height=1080, fps=30, crf=18, preset='slow').items():
        export.setdefault(k, v)
    if fps is not None: export['fps'] = fps
    if any(export[k] <= 0 for k in ('width', 'height', 'fps')) or export['width'] % 2 or export['height'] % 2:
        raise ValueError('Dimensions must be positive even numbers; FPS must be positive')
    known = set()
    previous_end = 0
    for event in cfg['timeline']:
        event['time'] = round(resolve(event['at'], cues)*export['fps'])/export['fps']
        event['duration'] = round(event.get('duration', .5)*export['fps'])/export['fps']
        if event['time'] < previous_end - 1e-6 or event['duration'] < 1/export['fps']:
            raise ValueError('Overlapping/out-of-order event or sub-frame duration: ' + str(event))
        previous_end = event['time'] + event['duration']
        if previous_end > audio_duration + 1/export['fps']:
            raise ValueError('Event extends beyond audio')
        if any(a['op'] == 'clear' for a in event['actions']) and len(event['actions']) != 1:
            raise ValueError('clear must be the only action in its event')
        touched = set()
        for action in event['actions']:
            if cfg['mode'] not in action.get('modes', ['basic', 'advanced']):
                continue
            op = action['op']
            if op == 'clear':
                known.clear()
                continue
            if op not in ('add', 'remove', 'replace', 'move', 'pulse', 'rotate'):
                raise ValueError('Unknown operation ' + op)
            ident = action['id']
            # Skip chapter/section title objects (filtered at render time)
            if ident == 'section':
                continue
            if ident in touched:
                raise ValueError('One action per object per event required')
            touched.add(ident)
            if op == 'add':
                if ident in known:
                    raise ValueError('Duplicate object: ' + ident)
                known.add(ident)
            elif ident not in known:
                raise ValueError('Missing object: ' + ident)
            if op == 'remove':
                known.remove(ident)
            if op in ('add', 'replace'):
                spec = action['object']
                kind = spec['type']
                if kind not in ('text','math','rectangle','circle','dot','line','arrow','polygon','axes','plot','box','sphere','axes3d'):
                    raise ValueError('Unknown object type: ' + kind)
                if kind == 'plot' and len(spec['points']) < 2:
                    raise ValueError('Plot requires at least two points')
    cfg['cues'] = cues
    return cfg


def render_scene(cfg):
    from manim import (ThreeDScene, Text, MathTex, Rectangle, RoundedRectangle, Circle,
        Dot, Line, Arrow, Polygon, Axes, VMobject, Prism, Sphere, ThreeDAxes,
        FadeIn, FadeOut, Write, Create, Transform, Indicate, Rotate, VGroup,
        linear, smooth, config, tempconfig)
    import numpy as np
    colors = cfg['theme']
    def color(s):
        return colors.get(s, s)
    def vec(p):
        return np.array(list(p) + [0]*(3-len(p)), dtype=float)

    class Explainer(ThreeDScene):
        def get_moving_mobjects(self, *animations):
            # Redraw the complete sparse scene to avoid stale Cairo static layers
            # when text is transformed and later emphasized.
            return list(self.mobjects)

        def construct(self):
            objects = {}
            specs = {}
            issues = []
            def build(s):
                s = {**s, **s.get(cfg['mode'], {})}
                kind = s['type']
                c = color(s.get('color', 'ink'))
                if kind == 'text':
                    obj = Text(s['text'], font=colors.get('font', 'Noto Sans'), font_size=s.get('size', 32), color=c)
                elif kind == 'math':
                    obj = MathTex(s['tex'], font_size=s.get('size', 60), color=c)
                    for token, shade in s.get('tex_colors', {}).items():
                        obj.set_color_by_tex(token, color(shade), substring=False)
                elif kind == 'rectangle':
                    obj = RoundedRectangle(width=s.get('width', 2), height=s.get('height', 1), corner_radius=s.get('radius', .12), color=c)
                elif kind in ('circle', 'dot'):
                    obj = (Circle if kind == 'circle' else Dot)(radius=s.get('radius', .3), color=c)
                elif kind in ('line', 'arrow'):
                    obj = (Line if kind == 'line' else Arrow)(vec(s['start']), vec(s['end']), color=c, **({'buff':0} if kind == 'arrow' else {}))
                elif kind == 'polygon':
                    obj = Polygon(*[vec(p) for p in s['points']], color=c)
                elif kind == 'axes':
                    obj = Axes(x_range=s.get('x_range', [0, 5, 1]), y_range=s.get('y_range', [0, 5, 1]), x_length=s.get('width', 5), y_length=s.get('height', 3), axis_config={'color':c, 'include_tip':False})
                elif kind == 'plot':
                    obj = VMobject(color=c).set_points_as_corners([vec(p) for p in s['points']])
                elif kind == 'box':
                    if cfg['mode'] == 'advanced':
                        obj = Prism(dimensions=s.get('dimensions',[1.4,1.4,1.4]), fill_color=c, fill_opacity=1, stroke_width=1)
                        obj.rotate(.95, axis=np.array([1,0,0])).rotate(-.35, axis=np.array([0,0,1]))
                    else:
                        obj = RoundedRectangle(width=s.get('dimensions',[1.4,1.4])[0], height=s.get('dimensions',[1.4,1.4])[1], corner_radius=.12, color=c, fill_opacity=.22)
                elif kind == 'sphere':
                    obj = Sphere(radius=s.get('radius',1), resolution=(16,24), fill_color=c, fill_opacity=1) if cfg['mode']=='advanced' else Circle(radius=s.get('radius',1), color=c, fill_opacity=.25)
                elif kind == 'axes3d':
                    obj = ThreeDAxes(x_length=4,y_length=4,z_length=3).rotate(.9,axis=np.array([1,0,0]))
                if 'fill_opacity' in s:
                    obj.set_fill(c, opacity=s['fill_opacity'])
                if 'stroke_width' in s:
                    obj.set_stroke(width=s['stroke_width'])
                if 'max_width' in s and obj.width > s['max_width']:
                    obj.scale_to_fit_width(s['max_width'])
                if 'position' in s:
                    obj.move_to(vec(s['position']))
                return obj

            end = math.ceil(cfg['duration']*cfg['export']['fps'] - 1e-8)/cfg['export']['fps']
            for event_index, event in enumerate(cfg['timeline'], 1):
                at = event['time']
                if at >= end and not cfg.get('_audit'):
                    break
                print(f'Rendering event {event_index}/{len(cfg["timeline"])} at {at:.2f}s', flush=True)
                if at > self.time + 1e-6 and not cfg.get('_audit'):
                    self.wait(at-self.time)
                animations = []
                for action in event['actions']:
                    if cfg['mode'] not in action.get('modes', ['basic', 'advanced']):
                        continue
                    op = action['op']
                    ident = action.get('id')
                    # Skip chapter/section title objects so they don't render
                    if ident == 'section':
                        continue
                    if op == 'clear':
                        animations.extend(FadeOut(o) for o in objects.values())
                        objects.clear()
                        specs.clear()
                    elif op == 'add':
                        obj = build(action['object'])
                        objects[ident] = obj
                        specs[ident] = action['object']
                        animation = action.get('animation','fade')
                        animations.append({'fade':FadeIn, 'write':Write, 'create':Create}[animation](obj))
                    elif op == 'replace':
                        target = build(action['object'])
                        specs[ident] = action['object']
                        if cfg.get('_audit'): objects[ident] = target
                        else: animations.append(Transform(objects[ident], target))
                    elif op == 'remove':
                        animations.append(FadeOut(objects.pop(ident)))
                        specs.pop(ident)
                    elif op == 'pulse':
                        animations.append(Indicate(objects[ident], color=color(action.get('color','accent')), scale_factor=action.get('scale',1.12)))
                    elif op == 'move':
                        if cfg.get('_audit'): objects[ident].move_to(vec(action['to']))
                        animations.append(objects[ident].animate(rate_func=(lambda t:t*t) if action.get('rate')=='accelerate' else linear).move_to(vec(action['to'])))
                    elif op == 'rotate':
                        animations.append(Rotate(objects[ident], angle=action.get('angle',math.pi/2), axis=vec(action.get('axis',[0,1,0]))))
                if cfg.get('_audit'):
                    labels=[]
                    for name, obj in objects.items():
                        if not obj.has_points() and not len(obj.submobjects): continue
                        l,r,b,t=obj.get_left()[0],obj.get_right()[0],obj.get_bottom()[1],obj.get_top()[1]
                        if l < -6.85 or r > 6.85 or b < -3.7 or t > 3.7:
                            issues.append(f'{at:.2f}s: {name} exceeds safe frame')
                        if specs[name]['type'] in ('text','math'):
                            labels.append((name,l,r,b,t))
                    for i,(n,l,r,b,t) in enumerate(labels):
                        for m,ll,rr,bb,tt in labels[i+1:]:
                            if min(r,rr)-max(l,ll)>.02 and min(t,tt)-max(b,bb)>.02:
                                issues.append(f'{at:.2f}s: labels {n} / {m} overlap')
                    continue
                run = min(event['duration'], end-self.time)
                if animations and run > 1e-6:
                    self.play(*animations, run_time=run)
            if cfg.get('_audit'):
                (Path(cfg['_work'])/'layout-audit.json').write_text(json.dumps({'events':len(cfg['timeline']),'issues':issues},indent=2))
                if issues: raise ValueError('Layout audit failed: '+ '; '.join(issues[:12]))
                print('Layout audit passed: safe frame and no label collisions.', flush=True)
                return
            if self.time < end - 1e-6:
                self.wait(end-self.time)

    out = Path(cfg['_work'])
    with tempconfig(dict(pixel_width=cfg['export']['width'], pixel_height=cfg['export']['height'], frame_rate=cfg['export']['fps'],
            frame_width=14.222222, frame_height=8, background_color=colors['background'],
            media_dir=str(out/'media'), output_file='picture', disable_caching=True,
            renderer='cairo', verbosity='WARNING', progress_bar='none')):
        scene = Explainer()
        if cfg.get('_audit'):
            scene.construct()
            return None
        scene.render()
        return Path(scene.renderer.file_writer.movie_file_path)


def write_captions(cfg, path):
    # Phrase captions retain exact word boundaries without flashing single words.
    cues = cfg['cues']
    groups, current = [], []
    overrides = cfg.get('caption_corrections', {})
    for index, cue in cues.items():
        current.append({**cue, 'text':overrides.get(str(index),cue['text'])})
        if len(current) >= 7 or re.search(r'[.!?,]$', current[-1]['text']):
            groups.append(current); current=[]
    if current: groups.append(current)
    def stamp(t):
        n = round(t*1000)
        return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
    blocks=[]
    for group in groups:
        start, end = group[0]['start'], min(group[-1]['end'],cfg['duration'])
        if start >= cfg['duration']: break
        blocks.append(f'{len(blocks)+1}\n{stamp(start)} --> {stamp(end)}\n'+ ' '.join(c['text'] for c in group))
    path.write_text('\n\n'.join(blocks)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(Path(__file__).resolve().parent/'config.json'))
    parser.add_argument('--fps', type=int, help='Output frames per second')
    parser.add_argument('--resolution', choices=['720p','1080p','4k'], help='Output dimensions')
    parser.add_argument('--audit-layout', action='store_true', help='Check all layouts without rendering video')
    parser.add_argument('--mode', choices=['basic','advanced'])
    parser.add_argument('--duration', type=float, help='Render first N seconds, including matching audio')
    parser.add_argument('--output', help='Output MP4 path')
    parser.add_argument('--validate', action='store_true', help='Validate timing and assets without rendering')
    parser.add_argument('--encode-only', action='store_true', help='Re-encode an existing picture render; do not change visual config')
    parser.add_argument('--subtitles', action='store_true', help='Include a selectable subtitle track in the MP4')
    parser.add_argument('--local', action='store_true', help='Use locally installed Manim instead of Docker')
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inside:
        cfg = json.loads(Path(args.config).read_text())
        picture = render_scene(cfg)
        if not cfg.get('_audit'):
            (Path(cfg['_work'])/'picture_path.txt').write_text(str(picture))
        return
    if not Path(args.config).exists() and Path(args.config).resolve() == Path(__file__).resolve().parent/'config.json':
        from generate_config import generate
        generate()
    cfg = prepare(args.config, args.mode, args.duration, args.fps)
    if args.fps:
        if args.fps < 1: raise ValueError('FPS must be positive')
        cfg['export']['fps'] = args.fps
    if args.resolution:
        cfg['export']['width'], cfg['export']['height'] = {'720p':(1280,720),'1080p':(1920,1080),'4k':(3840,2160)}[args.resolution]
    cfg['_audit'] = args.audit_layout
    if args.validate:
        print(f"Valid: {cfg['mode']}, {cfg['duration']:.3f}s, {len(cfg['timeline'])} events, {len(cfg['cues'])} words")
        return
    root = Path(args.config).resolve().parent
    output = Path(args.output or root/'output'/f"{cfg.get('slug','explainer')}_{cfg['mode']}{'_preview' if args.duration else ''}.mp4").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    work = root/'build'/output.stem
    work.mkdir(parents=True,exist_ok=True)
    cfg['_work'] = str(work)
    (work/'resolved_config.json').write_text(json.dumps(cfg,indent=2))
    if args.subtitles:
        captions = work/'captions.srt'
        write_captions(cfg,captions)
    if args.encode_only:
        picture = Path((work/'picture_path.txt').read_text())
        if not picture.is_file():
            raise ValueError('No completed picture render to encode')
    elif not args.local:
        script = Path(__file__).resolve()
        if script.parent != root:
            raise ValueError('Keep editor.py and config.json in the same project directory')
        if not output.is_relative_to(root):
            raise ValueError('Docker output must be within the project directory')
        for key in ('audio', 'subtitles'):
            if not Path(cfg[key]).is_relative_to(root):
                raise ValueError('Docker assets must be within the project directory')
        cmd = ['docker','run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}',
               '-e','HOME=/tmp','-v',f'{root}:{root}','-w',str(root),
               cfg.get('docker_image','manimcommunity/manim:latest'),'python',str(script),
               '--inside','--config',str(work/'resolved_config.json')]
        subprocess.run(cmd,check=True)
        if args.audit_layout: return
        picture = Path((work/'picture_path.txt').read_text())
    else:
        picture = render_scene(cfg)
        if args.audit_layout: return
        (work/'picture_path.txt').write_text(str(picture))
    ex = cfg['export']
    command = ['ffmpeg','-y','-v','warning','-i',str(picture),'-i',cfg['audio']]
    if args.subtitles:
        command += ['-i',str(captions)]
    command += ['-map','0:v:0','-map','1:a:0']
    if args.subtitles:
        command += ['-map','2:s:0']
    command += ['-t',str(cfg['duration']),
        '-c:v','libx264','-profile:v','high','-pix_fmt','yuv420p','-crf',str(ex['crf']),'-preset',ex['preset'],'-threads','2',
        '-r',str(ex['fps']),'-vf','scale=out_color_matrix=bt709:out_range=tv','-color_range','tv','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
        '-c:a','aac','-b:a','320k','-ar','48000','-ac','2']
    if args.subtitles:
        command += ['-c:s','mov_text','-metadata:s:s:0','language=eng']
    command += ['-movflags','+faststart',str(output)]
    subprocess.run(command,check=True)
    report = probe(output)
    (output.with_suffix('.probe.json')).write_text(json.dumps(report,indent=2))
    print('Exported:',output)

if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        sys.exit(f'Error: {exc}')
