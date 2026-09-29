import bisect
import math
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageOps
from .gif import GifAnimation
from .geometry import smooth, lerp_box
from .artwork import ArtworkMixin
from .animation import DrawingMixin
from .overlays import OverlayMixin
from .transitions import TransitionMixin
from .modes import MODES

class Renderer(ArtworkMixin, DrawingMixin, OverlayMixin, TransitionMixin):
    def __init__(self,c,base,mode='available-space'):
        self.c,self.base=c,base
        if mode not in MODES:
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
            d=ImageDraw.Draw(self.blank); color=c['board']['line_color']; width=max(1, round(c['board']['line_width']*self.w/1920))
            d.rounded_rectangle(self.board_rect,radius=round(c['board']['corner_radius']*self.w/1920),outline=color,width=width)
            for j in (1,2):
                x=round(m+j*self.cw); d.line((x,m,x,self.h-m),fill=color,width=width)
            d.line((m,round(m+self.ch),self.w-m,round(m+self.ch)),fill=color,width=width)
        self.hand=None
        self.swipe_hand = None
        swipe = c.get('swipe_hand', {})
        if swipe.get('enabled', False):
            with Image.open(base / swipe['path']) as im:
                raw = ImageOps.exif_transpose(im).convert('RGBA')
            height = round(self.h * swipe['height_fraction'])
            self.swipe_hand = raw.resize((max(1, round(raw.width*height/raw.height)), height), Image.Resampling.LANCZOS)
            self.swipe_tip = (swipe['tip'][0]*self.swipe_hand.width,
                              swipe['tip'][1]*self.swipe_hand.height)
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
        if self.mode in MODES and MODES[self.mode] is not None:
            return MODES[self.mode](self, i, t)
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
            canvas.paste(art,box[:2])
            if self.swipe_hand is not None:
                self.paste_swipe_hand(canvas, box, phase)
            else:
                self.gestures(canvas,box,phase)
            return canvas
        p=(t-b['draw_start'])/(b['draw_end']-b['draw_start'])
        art,tip=self.reveal(i,p)
        canvas=Image.new('RGB',(self.w,self.h),self.c['board']['background'])
        canvas.paste(art,self.focus[:2])
        if tip is not None:
            fade=min(1,max(0,(1-p)/.05))
            self.paste_hand(canvas,(self.focus[0]+tip[0],self.focus[1]+tip[1]),opacity=fade,motion_time=t)
        return canvas
