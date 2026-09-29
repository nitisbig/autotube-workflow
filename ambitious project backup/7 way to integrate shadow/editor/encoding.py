"""CPU and Linux VA-API encoding, with a real hardware preflight."""
import subprocess
from pathlib import Path

COLOR_FILTER = 'scale=in_range=pc:out_range=tv:out_color_matrix=bt709'


def encoding_options(output, gpu=False, device='/dev/dri/renderD128'):
    if gpu:
        return (['-vaapi_device', str(device)],
                ['-vf', COLOR_FILTER + ',format=nv12,hwupload',
                 '-c:v', 'h264_vaapi', '-rc_mode', 'CQP', '-qp', '20',
                 '-profile:v', 'high', '-bf', '0', '-g', str(output['fps']*2)])
    return ([], ['-vf', COLOR_FILTER + ',format=yuv420p',
                 '-c:v', 'libx264', '-preset', output['preset'],
                 '-crf', str(output['crf']), '-profile:v', 'high',
                 '-g', str(output['fps']*2), '-pix_fmt', 'yuv420p'])


def check_gpu(output, device):
    hint = ('Check that your Mesa VA-API driver supports H.264 encoding and that '
            'you have access to the render device. Try --res 1080p if a higher '
            'resolution fails, or use --gpu false for CPU encoding.')
    if not Path(device).exists():
        raise RuntimeError(f'GPU device {device} is unavailable. '
                           'Use --gpu-device /dev/dri/renderD129 if appropriate. ' + hint)
    inputs, encoding = encoding_options(output, True, device)
    # Exercise RGB conversion, upload and encoding at the requested dimensions.
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', *inputs,
               '-f', 'lavfi', '-i',
               f'color=black:s={output["width"]}x{output["height"]}:r={output["fps"]},format=rgb24',
               '-frames:v', '3', *encoding, '-an', '-f', 'null', '-']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('GPU encoding test timed out. ' + hint) from exc
    if result.returncode:
        raise RuntimeError('GPU encoding test failed. ' + hint + '\n' + result.stderr)
    print(f'GPU encoding verified: H.264 VA-API on {device} (QP 20).', flush=True)
