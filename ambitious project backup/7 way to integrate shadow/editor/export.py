import math
import subprocess
import tempfile
import time
from pathlib import Path
from .audio import audio_pauses, prepare_audio
from .renderer import Renderer
from .encoding import encoding_options

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
    device_options, video_options = encoding_options(
        o, getattr(args, 'gpu', False), getattr(args, 'gpu_device', '/dev/dri/renderD128'))
    print('Encoder: ' + ('GPU H.264 VA-API' if getattr(args, 'gpu', False) else 'CPU libx264'), flush=True)
    with tempfile.NamedTemporaryFile(prefix='.whiteboard-',suffix='.mp4',dir=output.parent,delete=False) as f: temporary=Path(f.name)
    command=['ffmpeg','-hide_banner','-loglevel','warning','-y',
        *device_options,
        '-f','rawvideo','-pixel_format','rgb24','-video_size',f'{o["width"]}x{o["height"]}',
        '-framerate',str(fps),'-i','pipe:0','-ss',str(start),'-i',str(audio_path),
        '-map','0:v:0','-map','1:a:0','-t',f'{duration:.6f}',
        *video_options,
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
