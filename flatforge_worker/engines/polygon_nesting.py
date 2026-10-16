"""Conservative vertex-alignment nesting for simple, hole-free polygons."""
import math

EPS = 1e-7
MAX_PARTS = 100
MAX_VERTICES = 200


def _number(v, label, zero=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or (v < 0 if zero else v <= 0):
        raise ValueError(f"{label} must be a finite {'non-negative' if zero else 'positive'} number")
    return float(v)


def _cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _dist(a,b):
    return math.hypot(a[0]-b[0],a[1]-b[1])


def _on(a,b,p):
    return abs(_cross(a,b,p)) < EPS and min(a[0],b[0])-EPS <= p[0] <= max(a[0],b[0])+EPS and min(a[1],b[1])-EPS <= p[1] <= max(a[1],b[1])+EPS


def _crosses(a,b,c,d):
    ab1,ab2,cd1,cd2=_cross(a,b,c),_cross(a,b,d),_cross(c,d,a),_cross(c,d,b)
    return ((ab1 > EPS and ab2 < -EPS or ab1 < -EPS and ab2 > EPS) and (cd1 > EPS and cd2 < -EPS or cd1 < -EPS and cd2 > EPS))


def _inside(p, poly):
    x,y=p; inside=False
    for i,a in enumerate(poly):
        b=poly[(i+1)%len(poly)]
        if _on(a,b,p): return False
        if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]: inside=not inside
    return inside


def _validate(points, label):
    if not isinstance(points,list) or not 3 <= len(points) <= MAX_VERTICES:
        raise ValueError(f"{label}.points must contain 3 to {MAX_VERTICES} vertices")
    p=[]
    for i,xy in enumerate(points):
        if not isinstance(xy,(list,tuple)) or len(xy)!=2: raise ValueError(f"{label}.points[{i}] must be [x, y]")
        p.append((_number(xy[0],f"{label}.x",True),_number(xy[1],f"{label}.y",True)))
    if len(set(p))<3: raise ValueError(f"{label} needs three distinct vertices")
    area=sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))
    n=len(p)
    for i in range(n):
        a,b=p[i],p[(i+1)%n]
        if _dist(a,b)<EPS: raise ValueError(f"{label} has a zero-length edge")
        for j in range(i+1,n):
            if j==i or j==(i+1)%n or i==(j+1)%n: continue
            c,d=p[j],p[(j+1)%n]
            if _crosses(a,b,c,d) or _on(a,b,c) or _on(a,b,d):
                raise ValueError(f"{label} must be a simple polygon without self-intersections")
    if abs(area)<EPS: raise ValueError(f"{label} polygon area must be positive")
    minx,miny=min(x for x,y in p),min(y for x,y in p)
    return [(x-minx,y-miny) for x,y in p]


def _bounds(p):
    return min(x for x,y in p),min(y for x,y in p),max(x for x,y in p),max(y for x,y in p)


def _distance_segment(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    t=0 if den<EPS else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return _dist(p,(a[0]+t*dx,a[1]+t*dy))


def _edge_distance(a,b,c,d):
    if _crosses(a,b,c,d) or _on(a,b,c) or _on(a,b,d) or _on(c,d,a) or _on(c,d,b): return 0.0
    return min(_distance_segment(a,c,d),_distance_segment(b,c,d),_distance_segment(c,a,b),_distance_segment(d,a,b))


def _conflict(a,b,gap):
    if len(a) == len(b) and set(map(tuple, a)) == set(map(tuple, b)): return True
    for i,p in enumerate(a):
        q=a[(i+1)%len(a)]
        for j,r in enumerate(b):
            s=b[(j+1)%len(b)]
            distance=_edge_distance(p,q,r,s)
            if distance < gap-EPS or (gap<=EPS and _crosses(p,q,r,s)): return True
    return _inside(a[0],b) or _inside(b[0],a)


def nest_polygon_parts(params, scoring="compact_envelope"):
    if scoring not in ("compact_envelope", "bottom_left"):
        raise ValueError("scoring must be compact_envelope or bottom_left")
    if not isinstance(params,dict): raise ValueError("request must be an object")
    parts=params.get("parts")
    if not isinstance(parts,list) or not parts: raise ValueError("'parts' must be a non-empty list")
    if len(parts)>MAX_PARTS: raise ValueError(f"polygon nesting supports at most {MAX_PARTS} parts")
    sw=_number(params.get("sheet_width",1000),"sheet_width")
    sh=_number(params.get("sheet_height",1000),"sheet_height")
    margin=_number(params.get("margin",0),"margin",True); gap=_number(params.get("gap",0),"gap",True)
    rotate=params.get("allow_rotation",True)
    if not isinstance(rotate,bool): raise ValueError("allow_rotation must be a boolean")
    if margin*2>=sw or margin*2>=sh: raise ValueError("margin leaves no usable sheet area")
    normalized=[]; seen=set(); total_vertices=0
    for i,part in enumerate(parts):
        if not isinstance(part,dict): raise ValueError(f"parts[{i}] must be an object")
        pid=part.get("id",str(i+1))
        if not isinstance(pid,(str,int)) or isinstance(pid,bool): raise ValueError(f"parts[{i}].id must be a string or integer")
        if str(pid) in seen: raise ValueError(f"duplicate part id: {pid}")
        seen.add(str(pid))
        if "points" in part:
            points=_validate(part.get("points"),f"parts[{i}]")
        else:
            rw=_number(part.get("width"),f"parts[{i}].width")
            rh=_number(part.get("height"),f"parts[{i}].height")
            points=[(0.0,0.0),(rw,0.0),(rw,rh),(0.0,rh)]
        total_vertices+=len(points)
        if total_vertices>5000: raise ValueError("polygon nesting supports at most 5000 vertices in total")
        x0,y0,x1,y1=_bounds(points)
        area=abs(sum(points[k][0]*points[(k+1)%len(points)][1]-points[(k+1)%len(points)][0]*points[k][1] for k in range(len(points))))/2
        normalized.append({"id":pid,"points":points,"w":x1-x0,"h":y1-y0,"area":area})
    normalized.sort(key=lambda p:(-p["area"],-max(p["w"],p["h"]),str(p["id"])))
    placed=[]; unplaced=[]
    for part in normalized:
        original=part["points"]; w,h=part["w"],part["h"]
        orientations=[(original,False)]
        if rotate and not math.isclose(w,h,abs_tol=EPS): orientations.append(([(y,w-x) for x,y in original],True))
        best=None
        for poly,rotated in orientations:
            bx,by,bw,bh=_bounds(poly); w2,h2=bw-bx,bh-by
            if w2>sw-2*margin+EPS or h2>sh-2*margin+EPS: continue
            candidates={(margin,margin)}
            for ex in placed:
                eb=_bounds(ex["points"])
                candidates.add((eb[2]+gap,eb[1])); candidates.add((eb[0],eb[3]+gap)); candidates.add((eb[2]+gap,margin)); candidates.add((margin,eb[3]+gap))
                for vx,vy in ex["points"]:
                    for px,py in poly: candidates.add((vx-px,vy-py))
            for x,y in sorted(candidates,key=lambda p:(p[1],p[0])):
                if x<margin-EPS or y<margin-EPS or x+w2>sw-margin+EPS or y+h2>sh-margin+EPS: continue
                points=[(round(x+px,6),round(y+py,6)) for px,py in poly]
                if any(_conflict(points,ex["points"],gap) for ex in placed): continue
                # Prefer placements that keep the occupied envelope compact. This
                # improves on pure bottom-left selection without claiming optimality.
                all_points=[point for ex in placed for point in ex["points"]]+points
                min_x=min(p[0] for p in all_points); min_y=min(p[1] for p in all_points)
                max_x=max(p[0] for p in all_points); max_y=max(p[1] for p in all_points)
                envelope_w=max_x-min_x; envelope_h=max_y-min_y
                if scoring == "bottom_left":
                    # Reproduce the pre-0.7 placement preference for benchmark comparison.
                    score=(y, x, rotated)
                else:
                    score=(envelope_w*envelope_h, envelope_w+envelope_h, max_y, max_x, y, x, rotated)
                if best is None or score<best[0]: best=(score,x,y,w2,h2,rotated,points)
        if best is None: unplaced.append(part["id"]); continue
        _,x,y,w2,h2,rotated,points=best
        placed.append({"id":part["id"],"x":round(x,6),"y":round(y,6),"width":round(w2,6),"height":round(h2,6),"rotated_90":rotated,"points":[[x,y] for x,y in points],"area":round(part["area"],6)})
    area=sum(p["area"] for p in placed)
    return {"status":"partial" if unplaced else "ok","algorithm":("polygon_vertex_alignment_bottom_left_baseline" if scoring == "bottom_left" else "polygon_vertex_alignment_compact_envelope"),"sheet":{"width":sw,"height":sh,"margin":margin,"gap":gap},"placements":placed,"unplaced":unplaced,"utilization":round(area/(sw*sh),6),"placed_count":len(placed),"part_count":len(normalized),"warning":"Heurística poligonal por alineación de vértices y envolvente compacta para contornos simples sin agujeros; no garantiza óptimo. Verifica tolerancias, escala y ajustes de corte antes de fabricar."}
