import bisect
import math
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageOps
from .media import resolve_image
from .geometry import smooth

class OverlayMixin:
    def paste_swipe_hand(self, canvas, box, progress):
        """Keep the fingertips on the moving artwork, easing contact/release."""
        if self.swipe_hand is None or not 0 < progress < 1:
            return
        opacity = min(1, progress/.15, (1-progress)/.2)
        if opacity < 1/255:
            return
        hand = self.swipe_hand
        if opacity < 1:
            hand = hand.copy()
            hand.putalpha(hand.getchannel('A').point(lambda a: round(a*opacity)))
        point = ((box[0]+box[2])/2, (box[1]+box[3])/2)
        canvas.paste(hand, (round(point[0]-self.swipe_tip[0]),
                            round(point[1]-self.swipe_tip[1])), hand)

    @lru_cache(maxsize=8)
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
