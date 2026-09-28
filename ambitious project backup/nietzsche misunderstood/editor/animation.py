import bisect
import math
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageOps
from .media import resolve_image
from .geometry import smooth

class DrawingMixin:
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
