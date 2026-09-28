"""Render accumulating six-scene boards with configurable export quality."""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from .validation import validate
from .export import render
from .modes import MODES
RESOLUTIONS = {"1080p": (1920,1080), "2k": (2560,1440), "4k": (3840,2160)}

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config',type=Path,default=Path(__file__).resolve().parent.parent / 'config.json')
    parser.add_argument('--mode',choices=tuple(MODES),default=None,
                        help='Drawing mode (default: config animation.mode or available-space)')
    parser.add_argument('--validate',action='store_true',help='Check config and asset names without rendering')
    parser.add_argument('--duration',type=float,help='Render only this many seconds')
    parser.add_argument('--start',type=float,default=0,help='Preview start time in seconds')
    parser.add_argument('--output',help='Output MP4 path; relative to current directory')
    parser.add_argument('--overwrite',action='store_true',help='Replace an existing output after successful rendering')
    parser.add_argument('--res', choices=tuple(RESOLUTIONS), help='Export resolution: 1080p, 2k (2560x1440), 4k (3840x2160)')
    parser.add_argument('--fps', type=int, choices=(25,30,60), help='Export frames per second')
    args=parser.parse_args()
    try:
        config_path=args.config.expanduser().resolve(); base=config_path.parent
        c=json.loads(config_path.read_text())
        if args.res: c['output']['width'], c['output']['height'] = RESOLUTIONS[args.res]
        if args.fps: c['output']['fps'] = args.fps
        args.mode = args.mode or c.get('animation', {}).get('mode', 'available-space')
        if args.mode not in MODES: raise ValueError(f'Unknown mode: {args.mode}')
        if not math.isfinite(args.start) or args.start < 0 or args.start >= c['duration']:
            raise ValueError('--start is outside the timeline')
        if args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0):
            raise ValueError('--duration must be finite and positive')
        if (args.res or args.fps) and not args.output:
            original = Path(c['output']['path'])
            c['output']['path'] = str(original.with_name(f'{original.stem}_{c["output"]["height"]}p_{c["output"]["fps"]}fps.mp4'))
        validate(c,base)
        print(f'Validated {len(c["beats"])} images across {len(c["beats"])//6} boards; duration {c["duration"]:.3f}s',flush=True)
        if not args.validate: render(c,base,args)
        return 0
    except KeyboardInterrupt:
        print('Cancelled; incomplete temporary output removed.',file=sys.stderr); return 130
    except (ValueError,KeyError,OSError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f'Error: {exc}',file=sys.stderr); return 1
