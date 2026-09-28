import bisect
import math
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageOps

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
