def smooth(p):
    p = max(0.0, min(1.0, p))
    return p*p*(3-2*p)

def lerp_box(a,b,p):
    return tuple(round(x+(y-x)*p) for x,y in zip(a,b))
