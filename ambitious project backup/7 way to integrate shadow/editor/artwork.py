import bisect
import math
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageOps
from .media import resolve_image
from .geometry import smooth

class ArtworkMixin:
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

    @lru_cache(maxsize=2)
    def board(self,board_index,completed):
        canvas=self.blank.copy()
        for cell in range(completed):
            index=board_index*6+cell
            canvas.paste(self.thumbnail(index),self.cells[cell][:2])
        return canvas
