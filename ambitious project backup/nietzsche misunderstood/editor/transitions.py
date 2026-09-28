import bisect
import math
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageOps
from .media import resolve_image
from .geometry import smooth

class TransitionMixin:
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
