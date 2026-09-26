#!/usr/bin/env python3
"""Word-cue anchored storyboard for the complete Vectors in AI narration."""
import json
import math
from pathlib import Path
from editor import read_srt
ROOT = Path(__file__).resolve().parent

def generate():
    cues = read_srt(ROOT/'cue-per-word.srt')
    events = []
    serial = 0
    def anchor(t):
        return min(cues, key=lambda i: abs(cues[i]['start']-t))
    def event(t, *actions, duration=.5):
        events.append(dict(at={'cue':anchor(t)}, duration=duration, actions=list(actions)))
    def add(name, obj, animation='fade'):
        return dict(op='add', id=name, object=obj, animation=animation)
    def rep(name, obj): return dict(op='replace',id=name,object=obj)
    def text(s,x=0,y=0,size=38,color='ink',width=11):
        return dict(type='text',text=s,position=[x,y],size=size,color=color,max_width=width)
    def formula(s,x=0,y=0,size=58,color='ink',width=10):
        return dict(type='math',tex=s,position=[x,y],size=size,color=color,max_width=width)
    def line(a,b,color='grid',width=2):
        return dict(type='line',start=a,end=b,color=color,stroke_width=width)
    def arrow(a,b,color='yellow'):
        return dict(type='arrow',start=a,end=b,color=color,stroke_width=4)
    def dot(x,y,color='yellow',r=.075):
        return dict(type='dot',position=[x,y],radius=r,color=color)
    def rect(x,y,w,h,color='blue',fill=0):
        return dict(type='rectangle',position=[x,y],width=w,height=h,radius=.08,color=color,fill_opacity=fill,stroke_width=2)
    def scene(t, objects):
        nonlocal serial
        serial += 1
        if events:
            # Clear ends on the new scene's exact word onset.
            cid=anchor(t)
            events.append(dict(at={'cue':cid,'offset':-.3},duration=.3,actions=[{'op':'clear'}]))
        event(t,*[add(k,v,'create' if v['type'] in ('arrow','line','plot') else 'fade') for k,v in objects.items()],duration=.6)
    def grid(x=-3,y=-.2,w=5,h=4):
        d={}
        for i in range(6):
            xx=x-w/2+i*w/5
            d[f'gx{i}']=line([xx,y-h/2],[xx,y+h/2])
        for i in range(5):
            yy=y-h/2+i*h/4
            d[f'gy{i}']=line([x-w/2,yy],[x+w/2,yy])
        d['xaxis']=line([x-w/2,y-h/2],[x+w/2+.25,y-h/2],'blue')
        d['yaxis']=line([x-w/2,y-h/2],[x-w/2,y+h/2+.25],'blue')
        return d
    def vector(s,x=3,y=0,color='yellow'):
        return formula(r'\begin{bmatrix}'+r'\\'.join(s)+r'\end{bmatrix}',x,y,color=color)
    def network():
        d={}
        for layer in range(4):
            x=-4.5+3*layer
            for j in range(3):
                y=-1.6+1.6*j
                d[f'n{layer}{j}']=dot(x,y,'blue' if layer%2 else 'yellow',.13)
                if layer<3:
                    for k in range(3):
                        d[f'e{layer}{j}{k}']=line([x+.16,y],[x+2.84,-1.6+1.6*k],'grid',1)
        return d
    def cloud(labels):
        d=grid(0,0,10,4)
        for i,(label,x,y,col) in enumerate(labels):
            d[f'p{i}']=dot(x,y,col)
            
            if label: d[f'l{i}']=text(label,x,y+.36,26,col,2.5)
        return d

    # Opening: a restrained prompt feeding an abstract computer.
    scene(.06,{'prompt':rect(-3.7,.15,3.1,1.65,'muted'), 'question':text('?',-3.7,.15,72,'yellow'),
        'chip':rect(3.4,.15,1.8,1.8,'blue'), 'ai':text('AI',3.4,.15,46,'blue')})
    event(1.13,add('bridge',arrow([-1.25,.15],[2.05,.15],'blue')))
    event(2.64,rep('question',text('capital',-4.65,.2,34,'ink',2)),rep('prompt',rect(-3.7,.15,4.4,1.65,'muted')))
    event(4.01,add('france',text('France',-2.85,.2,34,'yellow',1.6)),duration=.4)
    event(5.66,add('words',text('WORDS',-3.7,1.65,25,'muted')),duration=.4)
    event(7.0,rep('ai',formula(r'0\;1',3.4,.15,40,'blue',1.3)),duration=.45)
    event(8.01,dict(op='pulse',id='question',color='yellow',scale=1.06),duration=.4)
    event(8.87,dict(op='pulse',id='france',color='yellow',scale=1.06),duration=.4)
    event(12.72,rep('question',text('0.17',-4.65,.2,32,'blue',1.8)),rep('france',text('−0.42',-2.85,.2,32,'yellow',1.6)),rep('words',text('NUMBERS',-3.7,1.65,25,'muted')))
    scene(16.96,{'word':text('France',-4,0,45), 'arr':arrow([-2.5,0],[-.7,0],'blue'),'values':vector(['0.17','-0.42','0.81'],1.4), 'label':text('Mathematics',1.4,-2.25,28,'muted')})
    event(24.25,rep('label',text('Vector',1.4,-2.25,34,'yellow')))
    scene(27.44,{**grid(), 'v':arrow([-5.5,-2.2],[-2.5,-.2]),'value':vector(['3','2'],3), 'label':text('Vector',3,2.2,34,'yellow')})
    event(33.4,add('dx',line([-5.5,-2.2],[-2.5,-2.2],'yellow',5)),add('three',text('3',-4,-2.7,30,'yellow')))
    event(35.0,add('dy',line([-2.5,-2.2],[-2.5,-.2],'blue',5)),add('two',text('2',-1.95,-1.2,30,'blue')))
    event(40.12,dict(op='pulse',id='dx',color='yellow'))
    event(43.08,dict(op='pulse',id='dy',color='blue'))
    scene(48.12,{'title':text('A list of numbers',0,2.5,38), 'list':vector(['3','2'],0)})
    event(52.0,rep('list',vector(['3','2','5'],0)))
    event(55.0,rep('list',formula(r'[\,x_1,\;x_2,\;\ldots,\;x_{1000}\,]',0,0,56,'yellow')))
    scene(61.28,{'meaning':text('Meaning',-3.8,0,44),'arrow':arrow([-1.8,0],[1.1,0],'blue'),'geo':text('Geometry',3.7,0,44,'yellow')})
    scene(66.0,{'cat':text('cat',-4,0,50,'yellow'),'dog':text('dog',0,0,50,'blue'),'car':text('car',4,0,50,'green')})
    event(71.88,add('relation',line([-3.3,-.65],[-.7,-.65],'yellow',3)))
    scene(75.16,{'animal':text('Animal',-1,2.25,30,'yellow'),'machine':text('Machine',2.8,2.25,30,'blue'),
        'cat':text('cat',-4,1,38,'yellow'),'dog':text('dog',-4,-.4,38,'blue'),'car':text('car',-4,-1.8,38,'green')})
    event(85.64,add('catv',formula(r'0.9\qquad\quad0.1',.9,1,46)))
    event(89.12,add('dogv',formula(r'0.85\qquad\;0.1',.9,-.4,46)))
    event(93.08,add('carv',formula(r'0.05\qquad0.95',.9,-1.8,46)))
    # Coordinates are precisely mapped: x=animal, y=machine; labels offset apart.
    emb={**grid(-2,0,5,4),'animal':text('Animal',-2,-2.65,26,'muted'),'machine':text('Machine',-2,2.6,26,'muted'),
        'catpt':dot(0,-1.6),'dogpt':dot(-.25,-1.6,'blue'),'carpt':dot(-4.25,1.8,'green'),
        'cat':text('cat',.45,-1.05,27,'yellow',1),'dog':text('dog',-.8,-1.05,27,'blue',1),'car':text('car',-3.7,1.7,27,'green',1),
        'key':text('Meaning → distance',3.8,.3,34,'ink',4.5)}
    scene(97.24,emb)
    event(101.12,dict(op='pulse',id='catpt'),dict(op='pulse',id='dogpt',color='blue'))
    event(110.8,rep('key',text('Embedding',3.8,.3,42,'yellow',4.5)))
    scene(115.2,{'label':text('cat',-4,0,48,'yellow'),'arrow':arrow([-2.9,0],[-1.3,0],'blue'),'v':vector(['0.17','-0.42','0.81','0.06',r'\vdots'],1.2), 'dim':text('Hundreds of dimensions',1.2,-2.75,28,'muted')})
    event(133.8,rep('dim',text('A learned pattern',1.2,-2.75,28,'muted')))
    scene(144.2,{**grid(), 'a':arrow([-5.5,-2.2],[-1.2,.9]),'b':arrow([-5.5,-2.2],[-1.7,1.35],'blue'),'eq':formula(r'\mathbf a\cdot\mathbf b',3,1,58), 'name':text('Dot product',3,-1,32,'yellow')})
    event(151.48,rep('eq',formula(r'(3)(2)+(2)(1)',3,1,44,width=5)),rep('name',formula('=8',3,-1,56,'yellow')))
    event(160.32,rep('b',arrow([-5.5,-2.2],[-5,1.5],'blue')),rep('eq',formula(r'(3)(0)+(2)(1)',3,1,44,width=5)),rep('name',formula('=2',3,-1,56,'blue')))
    scene(167.8,{'cat':text('cat',-4,2,42,'yellow'),'chased':text('chased',0,2,42),'mouse':text('mouse',4,2,42,'blue'),
        'a':vector(['.2','.8'], -4,-.5),'b':vector(['.6','-.1'],0,-.5,'ink'),'c':vector(['.3','.7'],4,-.5,'blue')})
    event(175.64,add('link1',arrow([-2.8,-.5],[-1.2,-.5],'muted')),add('link2',arrow([1.2,-.5],[2.8,-.5],'muted')))
    # Pixel-art dog, composed from vector rectangles; no external image dependency.
    pixels={}
    pattern=['000000000000','001100001100','011111111110','011211112110','001111111100','000113311000','000011110000','000001100000']
    palette={'1':'#BFA580','2':'#F5F5F5','3':'#5A4436'}
    for row,s in enumerate(pattern):
        for col,ch in enumerate(s):
            if ch!='0': pixels[f'px{row}_{col}']=rect(-4.7+col*.27,1.1-row*.27,.26,.26,palette[ch],1)
    scene(181.2,{**pixels,'v':vector(['0.24','0.83','-0.12'],3),'arrow':arrow([-.7,0],[1.25,0],'blue'),'label':text('Pixels → numbers',-3.2,-2.2,30,'muted')})
    scene(191.12,{'edge':rect(-4,0,1.5,1.5,'yellow'),'e':text('Edges',-4,-1.6,30,'yellow'),'a':arrow([-2.9,0],[-1.4,0],'blue'),
        'pattern':rect(0,0,1.7,2,'blue'),'p':text('Patterns',0,-1.6,30,'blue'),'b':arrow([1.4,0],[2.9,0],'blue'),'obj':text('dog',4,0,45,'green'),'o':text('Objects',4,-1.6,30,'green')})
    event(205.88,rep('pattern',vector(['.24','.83'],0,0,'blue')))
    scene(209.68,{'image':rect(-4,1,2,1.7,'blue'),'label':text('Image',-4,-.5,30,'blue'),'word':text('dog',-4,-2,40,'yellow'),
        'a':arrow([-2.5,1],[-.5,.1],'blue'),'b':arrow([-2.5,-2],[-.5,-.4],'yellow'),'v':vector(['.24','.83','-.12'],2),'key':text('Shared space',2,-2.5,30,'muted')})
    scene(224.68,{'v':vector(['3','2'],-4),'m':formula(r'\begin{bmatrix}0&-1\\1&0\end{bmatrix}',0,0,56,'blue'),'out':vector(['-2','3'],4), 'a':arrow([-2.8,0],[-1.7,0],'muted'),'b':arrow([1.7,0],[2.8,0],'muted')})
    scene(234.4,{**grid(),'v':arrow([-5.5,-2.2],[-2.5,-.2]),'key':text('Rotate',3,.5,40,'yellow')})
    event(236.0,rep('v',arrow([-5.5,-2.2],[-4,1.4])),rep('key',text('Stretch',3,.5,40,'yellow')))
    event(237.2,rep('v',arrow([-5.5,-2.2],[-4.5,.2])),rep('key',text('Compress',3,.5,40,'blue')))
    scene(240.96,{**network(),'title':text('Vector → matrix → vector',0,2.8,36)})
    for t,layer in [(244.04,0),(246.68,1),(248.28,2),(250.0,3)]:
        event(t,*[dict(op='pulse',id=f'n{layer}{j}',color='yellow') for j in range(3)],duration=.7)
    scene(260.96,{'animal':text('animal',-4,1.3,42,'yellow'),'street':text('street',0,1.3,42,'blue'),'it':text('it',4,1.3,42), 'tired':text('tired',4,-1.4,35,'muted')})
    event(265.68,add('attend',arrow([3.4,.6],[-3.4,.6],'yellow')))
    event(269.0,add('name',text('Attention',0,-2.7,36,'yellow')))
    scene(274.12,{'q':vector(['q_1','q_2'],-4),'k':vector(['k_1','k_2'],0,0,'blue'),'v':vector(['v_1','v_2'],4,0,'green'),
        'ql':text('Query',-4,-2,30,'yellow'),'kl':text('Key',0,-2,30,'blue'),'vl':text('Value',4,-2,30,'green')})
    event(281.88,add('compare',formula(r'q\cdot k',0,2.5,45)))
    scene(286.64,{'it':text('it',0,-1.7,44),'animal':text('animal',-3.6,1.4,44,'yellow'),'street':text('street',3.6,1.4,44,'blue'),
        'strong':arrow([-.5,-1.1],[-3.3,.7],'yellow'),'weak':line([.5,-1.1],[3.3,.7],'grid',2)})
    scene(293.48,{**network(),'label':text('Attention across layers',0,2.8,34,'muted')})
    for t,l in [(295,0),(296.96,1),(299.4,2),(301,3)]: event(t,*[dict(op='pulse',id=f'n{l}{j}',color='blue') for j in range(3)])
    scene(304.64,{'prompt':text('The sky is …',0,2.4,42),'blue':text('blue',-4,.9,32,'blue'),'clear':text('clear',-4,-.4,32,'green'),'fall':text('falling',-4,-1.7,32,'muted')})
    event(313.32,add('bar1',rect(.2,.9,5,.35,'blue',.8)),add('bar2',rect(-1.407,-.4,1.786,.35,'green',.8)),add('bar3',rect(-2.1215,-1.7,.357,.35,'muted',.8)))
    event(322.92,add('p1',text('70%',3.7,.9,28,'blue')),add('p2',text('25%',3.7,-.4,28,'green')),add('p3',text('5%',3.7,-1.7,28,'muted')),add('toy',text('Illustrative probabilities',0,-2.8,22,'muted')))
    event(325.12,rep('prompt',text('The sky is blue',0,2.4,42)))
    scene(328.4,{**network(),'label':text('One word. Many calculations.',0,2.8,34)})
    scene(337.32,cloud([('Paris',-3,-.5,'yellow'),('France',-1.8,.8,'yellow'),('Tokyo',1,-.5,'blue'),('Japan',2.2,.8,'blue')]))
    event(343.08,add('paris',arrow([-2.85,-.3],[-1.95,.55],'yellow')))
    event(344.88,add('tokyo',arrow([1.15,-.3],[2.05,.55],'blue')))
    event(347.16,add('emotion',text('Emotions',-3,-2.8,28,'green')),add('code',text('Code',3,-2.8,28,'blue')))
    event(352.12,add('caveat',text('Structure ≠ human understanding',0,3,30,'muted')))
    scene(363.04,{**cloud([('',-3,-1,'blue'),('',-2,.4,'yellow'),('',-.5,1,'green'),('',1,-.8,'blue'),('',2.7,.7,'yellow')]),'key':text('Distributed patterns',0,3,38)})
    event(371.4,rep('key',text('Ideas → patterns',0,3,38)))
    event(372.92,rep('key',text('Relationships → directions',0,3,38)),add('direction',arrow([-2,.4],[2.7,.7],'yellow')))
    event(374.8,rep('key',text('Similarity → distance',0,3,38)))
    event(376.76,rep('key',text('Computation → movement',0,3,38)),dict(op='move',id='p0',to=[1,-.8]),duration=1.2)
    scene(383.48,{'kind':text('Text',-3.5,0,45),'arrow':arrow([-1.7,0],[.6,0],'blue'),'v':vector(['x_1','x_2',r'\vdots'],3)})
    for t,label in [(385.12,'Images'),(386.68,'Audio'),(388.16,'Video'),(389.8,'Preferences'),(392.08,'Documents')]: event(t,rep('kind',text(label,-3.5,0,40,width=4)))
    scene(396.36,{'a':vector(['.2','.8'],-4),'b':vector(['.3','.7'],4,0,'blue'),'compare':formula(r'\mathbf a\cdot\mathbf b',0,0,44),'label':text('Compare',0,2.5,36)})
    for t,label in [(398.92,'Search'),(401.44,'Recommend'),(404.48,'Connect images'),(407.44,'Connect context')]:event(t,rep('label',text(label,0,2.5,36)))
    scene(411.04,{'v':vector(['.17','-.42','.81'],0),'label':text('Just numbers',0,2.6,38)})
    scene(414.68,{**network(),'label':text('Learned transformations',0,2.8,36)})
    for t,l in [(417.36,0),(420.56,1),(422.32,2),(424.28,3)]:event(t,*[dict(op='pulse',id=f'n{l}{j}',color='yellow') for j in range(3)])
    scene(426.6,{'word':text('Words',-4,0,40),'a':arrow([-2.7,0],[-1.5,0],'blue'),'v':vector(['.17','-.42'],0),'b':arrow([1.5,0],[2.7,0],'blue'),'meaning':text('Meaning',4,0,38,'yellow')})
    event(431.08,rep('word',text('Numbers',-4,0,38,'blue')))
    event(433.84,rep('meaning',text('Points',4,0,38,'yellow')))
    event(437.32,dict(op='pulse',id='v',color='blue'))
    event(442.68,rep('meaning',text('Language',4,0,38,'yellow')))
    scene(445.8,{'arrow':arrow([-3,-1.5],[-.5,1.5]),'vector':vector(['3','2'],2),'title':text('Vectors',0,-2.6,46,'yellow')})
    # End exactly at the recording boundary; final spoken word receives emphasis.
    event(449.11,dict(op='pulse',id='title',color='yellow',scale=1.04),duration=.5)
    events.sort(key=lambda e:cues[e['at']['cue']]['start']+e['at'].get('offset',0))
    # Shorten transitions before the next cue without moving their word anchors.
    for i,e in enumerate(events[:-1]):
        a=cues[e['at']['cue']]['start']+e['at'].get('offset',0)
        b=cues[events[i+1]['at']['cue']]['start']+events[i+1]['at'].get('offset',0)
        e['duration']=min(e['duration'],max(1/30,math.floor((b-a)*30-1)/30))
    cfg=dict(version=1,slug='vectors_ai',mode='basic',audio='audio.mp3',subtitles='cue-per-word.srt',docker_image='sha256:d32b63fc124d',
        theme=dict(background='#000000',ink='#F4F4F0',muted='#8D969C',grid='#15313B',blue='#58A6BF',yellow='#F4EB49',green='#92B478',accent='#F4EB49',font='Noto Serif'),
        export=dict(width=1920,height=1080,fps=30,crf=18,preset='slow'),timeline=events)
    (ROOT/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    print(f'Built {len(events)} word-anchored events covering {len(cues)} words.')
    return cfg
if __name__=='__main__':generate()
