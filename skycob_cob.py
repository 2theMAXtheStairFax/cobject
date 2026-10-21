"""Generate the Sky Cob corn-cob shell and a STEP version of the payload chassis with M3 standoffs.

Outputs (next to this script):
  skycob_cob.step                  corn cob with a bottom-opening cavity sized from the stack STLs and
                                   parachute loops on the tip
  cobby19mm_cam_stand_standoffs.step  cobby19mm_cam_stand.stl converted to a solid, plus 4 M3 standoffs
                                   on the top face and M2 pilot holes in the 4 back pegs
  skycob_door.step                 the back-wall section cut out for RX/VTX access, as a separate door
  skycob_assembly.step            with --assembly: both of the above, chassis seated in the cob

The cavity is derived from the stack STLs (chassis + FC plate + receiver plate), so it tracks
changes to those parts. The cavity ceiling sits CEILING_CLEARANCE above the chassis top; the
standoffs plug up into sockets in the cob top and M3 screws go down through the top into them.

Run with a Python that has CadQuery installed:  python skycob_cob.py [--assembly]
"""
import math
import struct
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing)
from OCP.gp import gp_Pnt
from OCP.ShapeFix import ShapeFix_Solid
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

HERE = Path(__file__).parent
CHASSIS_FILE = "cobby19mm_cam_stand.stl"
STACK_FILES = [CHASSIS_FILE, "cobbyspeedy-top.stl", "cobby20x40.stl"]

# Stack envelope -> cavity wall, per face, in the STL frame. -y is the FC face (payload "top"),
# +y is the back (pegs + receiver plate), +-x are the sides.
CLEARANCE_SIDES = 10.0  # mm, -x and +x
CLEARANCE_FC = 10.0     # mm, -y
CLEARANCE_BACK = 25.0   # mm, +y
MOUTH_CLEARANCE = 20.0  # mm, stack bottom -> cavity mouth
CEILING_CLEARANCE = 0.0 # mm, chassis top -> cavity ceiling (0 = chassis top bears on the ceiling)
MIN_WALL = 4.0          # mm, thinnest core wall around the cavity (kernels add on top of this)
DOME_RATIO = 0.8        # tip length as a fraction of core radius (blunter = shorter screw access)

STANDOFF_OD = 7.0       # mm
STANDOFF_HEIGHT = 20.0  # mm, above the chassis top face
SOCKET_CLEAR = 0.4      # mm, socket diameter over STANDOFF_OD
STANDOFF_INSET = 4.0    # mm, standoff center in from the edges of the chassis top face
M3_PILOT = 2.5          # mm, self-tapping M3 into the printed standoff
PILOT_EXTRA = 6.0       # mm, pilot depth below the chassis top face
M3_CLEAR = 3.4          # mm, clearance hole through the plate above each socket
CEILING_PLATE = 5.0     # mm, solid plate above each socket that the screw head bears on
ACCESS_BORE = 7.0       # mm, screwdriver/head access from the outside of the cob down to the plate

RX_FILE = "cobby20x40.stl"  # receiver/VTX plate; side holes are centered on its height
SIDE_HOLE_DIA = 5.0     # mm
SIDE_HOLE_ANGLES = (45.0, 135.0, 225.0, 315.0)  # deg around the cob axis, between the loop axes

PORT_DROP = 40.0        # mm, RP-SMA bulkhead port this far below the side holes
PORT_ANGLE = 90.0       # deg around the cob axis (90 = +y, through the door in front of the VTX)
PORT_HOLE = 6.5         # mm, through hole for the 1/4"-36 bulkhead thread
PORT_PANEL = 2.5        # mm, wall left at the port for the connector to clamp through
PORT_SPOT = 12.0        # mm, diameter of the inside pocket and the outside flat (nut/washer seat)

DOOR_MARGIN = 5.0      # mm, door opening top above the installed RX/VTX plate
DOOR_FILLET = 5.0       # mm, rounding of the opening's top corners
DOOR_GAP = 0.3          # mm, door undersize on its sides and top, and clearance over the lips
LIP_WIDTH = 4.0         # mm, how far the cob's side rails reach in from the opening's sides
LIP_THICK = 4.0         # mm, lip thickness (along y)
DOOR_FLANGE = 3.5       # mm, door edge thickness left over the side lips, at the opening's side faces

M2_PILOT = 1.8        # mm, self-tapping M2 into the back pegs
PEG_HOLE_DEPTH = 12.0   # mm, from the peg tip
FLAT_SIDES = True       # build the frame's long (+-x) edges out flush with the pegs so it prints on its side

KERNEL_ROWS = 32        # kernel columns around the circumference (also the barrel's facet count)
KERNEL_PITCH = 10.5     # mm, vertical spacing between kernel rings
KERNEL_GAP = 1.0        # mm, groove between neighboring kernels at the core surface
KERNEL_HEIGHT = 3.5     # mm, how far a kernel stands proud of the core
KERNEL_EMBED = 1.0      # mm, kernel base buried in the core (more on the curved tip)
KERNEL_FILLET = 1.5     # mm, rounding on the exposed edges

# Parachute loops on the tip: tori standing in the YZ plane, lower half buried in the solid tip.
LOOP_X = (-30.0, 0.0, 30.0)  # mm, loop positions across the tip (clear of the access bores)
LOOP_RADIUS = 14.0      # mm, torus centerline radius
LOOP_THICKNESS = 10.0   # mm, cord section diameter
LOOP_RAISE = 5.0        # mm, torus center above the tip surface (opening clears the kernels)


def load_stl_mm(path):
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    tri = np.frombuffer(data[84:84 + n * 50],
                        dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return tri["v"].astype(float) * 1000.0  # exported in meters -> (n, 3, 3) mm


def mesh_to_bodies(tris):
    """Sew an STL into solids. The chassis STL is several overlapping closed bodies (frame, mount
    block, pegs) and is missing one triangle, so holes are capped and each shell becomes its own solid."""
    sew = BRepBuilderAPI_Sewing(1e-3)
    for a, b, c in tris:
        if np.linalg.norm(np.cross(b - a, c - a)) < 1e-9:
            continue
        poly = BRepBuilderAPI_MakePolygon(gp_Pnt(*a), gp_Pnt(*b), gp_Pnt(*c), True)
        sew.Add(BRepBuilderAPI_MakeFace(poly.Wire(), True).Face())
    sew.Perform()
    if sew.NbFreeEdges():
        free = [cq.Edge(sew.FreeEdge(i)) for i in range(1, sew.NbFreeEdges() + 1)]
        resew = BRepBuilderAPI_Sewing(1e-3)
        resew.Add(sew.SewedShape())
        for wire in cq.Wire.combine(free):
            resew.Add(cq.Face.makeFromWires(wire).wrapped)
        resew.Perform()
        assert resew.NbFreeEdges() == 0, "could not close the mesh"
        sew = resew
    bodies = []
    exp = TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL)
    while exp.More():
        fix = ShapeFix_Solid(BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(exp.Current())).Solid())
        fix.Perform()
        bodies.append(cq.Solid(fix.Solid()))
        exp.Next()
    return bodies


# --- stack envelope and chassis top face -------------------------------------------------------
chassis_tris = load_stl_mm(HERE / CHASSIS_FILE)
stack = np.vstack([load_stl_mm(HERE / f).reshape(-1, 3) for f in STACK_FILES])
lo, hi = stack.min(0), stack.max(0)
size = hi - lo

normals = np.cross(chassis_tris[:, 1] - chassis_tris[:, 0], chassis_tris[:, 2] - chassis_tris[:, 0])
normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
top_z = chassis_tris[:, :, 2].max()
top_face = chassis_tris[(normals[:, 2] > 0.99) & (np.abs(chassis_tris[:, :, 2].mean(1) - top_z) < 0.05)]
tx0, ty0 = top_face[:, :, :2].reshape(-1, 2).min(0) + STANDOFF_INSET
tx1, ty1 = top_face[:, :, :2].reshape(-1, 2).max(0) - STANDOFF_INSET
standoff_xy = [(tx0, ty0), (tx1, ty0), (tx0, ty1), (tx1, ty1)]  # chassis/STL frame

# Cavity footprint in the STL frame; the cob axis goes through its center.
cav_x0, cav_x1 = lo[0] - CLEARANCE_SIDES, hi[0] + CLEARANCE_SIDES
cav_y0, cav_y1 = lo[1] - CLEARANCE_FC, hi[1] + CLEARANCE_BACK
cav_x, cav_y = cav_x1 - cav_x0, cav_y1 - cav_y0
cav_h = size[2] + MOUTH_CLEARANCE + CEILING_CLEARANCE
corner_r = min(CLEARANCE_SIDES, CLEARANCE_FC, CLEARANCE_BACK)

# Chassis frame -> cob frame: cavity centered on the cob axis, stack bottom MOUTH_CLEARANCE above z=0.
to_cob = cq.Vector(-(cav_x0 + cav_x1) / 2, -(cav_y0 + cav_y1) / 2, MOUTH_CLEARANCE - lo[2])

# --- chassis with standoffs and back-peg holes -------------------------------------------------
bodies = mesh_to_bodies(chassis_tris)
# Left faceted: merging coplanar triangles (clean/UnifySameDomain) produces an invalid solid here.
chassis = bodies[0].fuse(*bodies[1:]).Solids()[0]

for x, y in standoff_xy:
    post = cq.Solid.makeCylinder(STANDOFF_OD / 2, STANDOFF_HEIGHT + 0.5, cq.Vector(x, y, top_z - 0.5))
    chassis = chassis.fuse(post)
for x, y in standoff_xy:
    depth = STANDOFF_HEIGHT + PILOT_EXTRA
    chassis = chassis.cut(cq.Solid.makeCylinder(M3_PILOT / 2, depth + 1,
                                                cq.Vector(x, y, top_z + STANDOFF_HEIGHT - depth)))

# Back pegs are the separate bodies that run along +y; drill each from its tip.
back_pegs = [bb for bb in (b.BoundingBox() for b in bodies) if bb.ylen > 2 * max(bb.xlen, bb.zlen)]
assert len(back_pegs) == 4, f"expected 4 back pegs, found {len(back_pegs)}"
for bb in back_pegs:
    tip = cq.Vector(bb.center.x, bb.ymax + 1, bb.center.z)
    chassis = chassis.cut(cq.Solid.makeCylinder(M2_PILOT / 2, PEG_HOLE_DEPTH + 1, tip, cq.Vector(0, -1, 0)))

# The pegs and FC-cover posts sit on the frame plate's edges and bulge ~2 mm past them, so on its side
# the chassis rests on those bumps. Trimming them would leave <1 mm around the M2 pilots, so instead
# add a rail along each plate edge (the largest +-x face) out to the outermost bulge. That stays inside
# the stack envelope the cavity is sized from.
side_rails = []
if FLAT_SIDES:
    tri_area = np.linalg.norm(np.cross(chassis_tris[:, 1] - chassis_tris[:, 0],
                                       chassis_tris[:, 2] - chassis_tris[:, 0]), axis=1) / 2
    for s in (-1, 1):
        m = normals[:, 0] * s > 0.99
        planes = np.round(chassis_tris[m][:, :, 0].mean(1), 2)
        xs, inv = np.unique(planes, return_inverse=True)
        edge = chassis_tris[m][inv == np.argmax(np.bincount(inv, tri_area[m]))].reshape(-1, 3)
        x_edge = edge[:, 0].mean()
        x_out = chassis_tris[:, :, 0].max() if s > 0 else chassis_tris[:, :, 0].min()
        (y0, z0), (y1, z1) = edge[:, 1:].min(0), edge[:, 1:].max(0)
        # No rail face may coincide with the faceted mesh (it leaves sliver holes when tessellated):
        # 0.5 mm into the plate, 0.05 mm proud of the outermost peg, 0.05 mm in from the plate faces.
        x0, x1 = sorted((x_edge - s * 0.5, x_out + s * 0.05))
        y0, y1, z0, z1 = y0 + 0.05, y1 - 0.05, z0 + 0.05, z1 - 0.05
        chassis = chassis.fuse(cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0)))
        side_rails.append((x_edge, x_out + s * 0.05, z0, z1))

# --- cob ---------------------------------------------------------------------------------------
core_r = math.hypot(cav_x / 2 - corner_r, cav_y / 2 - corner_r) + corner_r + MIN_WALL
dome_len = DOME_RATIO * core_r
z_top = cav_h + dome_len


def profile_r(z):
    if z <= cav_h:
        return core_r
    t = (z - cav_h) / dome_len
    return core_r * math.sqrt(max(1 - t * t, 0.0))


# Barrel is a prism with one flat per kernel column (apothem = core_r): sphere/plane intersections
# are exact circles, which keeps the STEP small. Sphere/cylinder intersections are B-splines and
# made the file several times bigger.
barrel = (cq.Workplane("XY").polygon(KERNEL_ROWS, 2 * core_r / math.cos(math.pi / KERNEL_ROWS))
          .extrude(cav_h).val())
tip_pts = [(profile_r(z), z) for z in np.linspace(cav_h, z_top, 25)[1:-1]] + [(0, z_top)]
dome = (cq.Workplane("XZ").moveTo(0, cav_h).lineTo(core_r, cav_h)
        .spline(tip_pts, tangents=[(0, 1), (-1, 0)], includeCurrent=True)
        .close().revolve(360, (0, 0, 0), (0, 1, 0)).val())


def tip_z(x, y):
    return cav_h + dome_len * math.sqrt(max(1 - (math.hypot(x, y) / core_r) ** 2, 0))


loops = [cq.Solid.makeTorus(LOOP_RADIUS, LOOP_THICKNESS / 2,
                            cq.Vector(x, 0, tip_z(x, 0) + LOOP_RAISE), cq.Vector(1, 0, 0))
         for x in LOOP_X]

# Kernels: flat rounded tiles in straight columns, one column per barrel facet. Each tile is built
# along +X (radial) with only its outer face and radial edges rounded, so the buried base stays a
# plain box.
facet_w = 2 * core_r * math.tan(math.pi / KERNEL_ROWS)


def kernel_tile(scale, embed):
    # The exposed underside is chamfered at 45 deg back to the core surface, so with the flat top of
    # the kernel below it forms a V groove and prints upright without overhangs.
    proud = KERNEL_HEIGHT * scale
    depth = embed + proud
    tile = (cq.Workplane("XY")
            .box(depth, (facet_w - KERNEL_GAP) * scale, (KERNEL_PITCH - KERNEL_GAP) * scale)
            .edges("|Y").edges("<Z").edges(">X").chamfer(proud * 0.999)
            .edges(">X or (|X and >Z)").fillet(min(KERNEL_FILLET * scale, proud * 0.45)).val())
    return tile.translate(cq.Vector(depth / 2 - embed, 0, 0))  # base at -embed, face at +height


def place_ring(tile, r, z, tilt):
    """Copies of tile around the axis at radius r and height z, outer face tilted up by tilt rad."""
    tile = tile.rotate(cq.Vector(), cq.Vector(0, 1, 0), -math.degrees(tilt)).translate(cq.Vector(r, 0, z))
    return [tile.rotate(cq.Vector(), cq.Vector(0, 0, 1), 360 * (k + 0.5) / KERNEL_ROWS)
            for k in range(KERNEL_ROWS)]


kernels = []
z = KERNEL_PITCH / 2
while z < cav_h:  # barrel: tiles sit flat on the facets (the last may overhang the tip start slightly)
    kernels += place_ring(kernel_tile(1.0, KERNEL_EMBED), core_r, z, 0.0)
    z += KERNEL_PITCH
t = (z - cav_h) / dome_len  # tip: walk the ellipse by arc length, shrinking tiles with radius
while core_r * math.cos(t) > 15:
    r, zt = core_r * math.cos(t), cav_h + dome_len * math.sin(t)
    scale = r / core_r
    tilt = math.atan2(math.sin(t) / dome_len, math.cos(t) / core_r)  # ellipse normal angle
    # Extra embed covers the gap between the flat tile base and the curved tip.
    kernels += place_ring(kernel_tile(scale, KERNEL_EMBED + 1.5), r, zt, tilt)
    t += KERNEL_PITCH * scale / math.hypot(core_r * math.sin(t), dome_len * math.cos(t))

cob = barrel.fuse(dome, *kernels, *loops).clean()

# Cavity: stack envelope grown by the per-face clearances, corners rounded, flat ceiling.
cavity = (cq.Workplane("XY").workplane(offset=-1).rect(cav_x, cav_y).extrude(cav_h + 1)
          .edges("|Z").fillet(corner_r).val())
base_trim = cq.Solid.makeBox(4 * core_r, 4 * core_r, 50, cq.Vector(-2 * core_r, -2 * core_r, -50))
cob = cob.cut(cavity).cut(base_trim)

# Standoff sockets up from the ceiling, M3 clearance through the plate above them, then access
# bores from the plate up through the tip.
socket_top = cav_h + STANDOFF_HEIGHT - CEILING_CLEARANCE
plate_top = socket_top + CEILING_PLATE
bore_depths = []
for x, y in standoff_xy:
    p = cq.Vector(x + to_cob.x, y + to_cob.y, 0)
    cob = cob.cut(cq.Solid.makeCylinder((STANDOFF_OD + SOCKET_CLEAR) / 2, socket_top - cav_h + 1,
                                        cq.Vector(p.x, p.y, cav_h - 1)))
    cob = cob.cut(cq.Solid.makeCylinder(M3_CLEAR / 2, CEILING_PLATE + 2, cq.Vector(p.x, p.y, socket_top - 1)))
    cob = cob.cut(cq.Solid.makeCylinder(ACCESS_BORE / 2, z_top, cq.Vector(p.x, p.y, plate_top)))
    bore_depths.append(tip_z(p.x, p.y) - plate_top)

rx = load_stl_mm(HERE / RX_FILE).reshape(-1, 3)

# Access door: the back (+y) wall across the full cavity width (taking the cavity's corner fillets
# with it), from the base up to DOOR_MARGIN above the installed RX/VTX plate.
#
# Lips: two plain rectangular rails up the opening's sides, LIP_WIDTH wide, sitting in the cavity
# corners (fused to the side faces) and stopping flat below the opening's top corner fillets. Their
# seat leaves DOOR_FLANGE of door at the side faces. The door's side edges are stepped full height
# to rest on them, so it pushes straight in from outside and sits flush; its top edge just meets
# the opening's top.
door_z1 = rx[:, 2].max() + to_cob.z + DOOR_MARGIN
side_seat = math.sqrt(core_r ** 2 - (cav_x / 2) ** 2) - DOOR_FLANGE
lip_x = cav_x / 2 - LIP_WIDTH  # inner edge of the side rails


def door_block(half_w, top):
    return (cq.Workplane("XZ").center(0, (top - 1) / 2).rect(2 * half_w, top + 1)
            .extrude(-(core_r + 20))  # XZ normal is -Y: extrude toward +y
            .edges("|Y and >Z").fillet(DOOR_FILLET).val())


def band(x_in, x_out, y0, y1):
    """Region x_in <= |x| <= x_out, y0..y1, from the cob base up."""
    h = 2 * cav_h
    w = x_out - x_in
    return (cq.Solid.makeBox(w, y1 - y0, h, cq.Vector(x_in, y0, 0))
            .fuse(cq.Solid.makeBox(w, y1 - y0, h, cq.Vector(-x_out, y0, 0))))


opening = door_block(cav_x / 2, door_z1)
rail_top = door_z1 - DOOR_FILLET
lips = band(lip_x, cav_x / 2, side_seat - LIP_THICK, side_seat).intersect(
    cq.Solid.makeBox(cav_x, core_r, rail_top, cq.Vector(-cav_x / 2, 0, 0)))
# Door: the removed wall less everything beside the rails at or below the seat, full height.
seats_g = opening.intersect(band(lip_x - DOOR_GAP, cav_x, -1, side_seat + DOOR_GAP))

door_part = cob.intersect(door_block(cav_x / 2 - DOOR_GAP, door_z1 - DOOR_GAP)).cut(seats_g)
cob = cob.cut(opening).fuse(lips)

# Radial side holes at the receiver/VTX plate's mid-height, measured from the bottom of the stack
# and taken from the cob base (not offset by MOUTH_CLEARANCE). Cut after the door so the lip layers
# stay straight along z and the door can slide; the holes go through cob and door alike.
side_hole_z = (rx[:, 2].min() + rx[:, 2].max()) / 2 - lo[2]
for a in SIDE_HOLE_ANGLES:
    d = cq.Vector(math.cos(math.radians(a)), math.sin(math.radians(a)), 0)
    hole = cq.Solid.makeCylinder(SIDE_HOLE_DIA / 2, core_r + 20, cq.Vector(0, 0, side_hole_z), d)
    cob = cob.cut(hole)
    door_part = door_part.cut(hole)

# RP-SMA bulkhead port: a PORT_PANEL wall with a through hole, a flat spot-faced just under the
# core surface outside (clear of the kernels) and a pocket thinning the wall from the cavity side.
port_z = side_hole_z - PORT_DROP
pd = cq.Vector(math.cos(math.radians(PORT_ANGLE)), math.sin(math.radians(PORT_ANGLE)), 0)
spot_r = core_r * math.cos(math.pi / KERNEL_ROWS) - 0.5  # flat across facet edges within the spot
port_cuts = [
    cq.Solid.makeCylinder(PORT_HOLE / 2, core_r + 20, cq.Vector(0, 0, port_z), pd),
    cq.Solid.makeCylinder(PORT_SPOT / 2, spot_r - PORT_PANEL, cq.Vector(0, 0, port_z), pd),
    cq.Solid.makeCylinder(PORT_SPOT / 2, 30, cq.Vector(0, 0, port_z) + pd * spot_r, pd),
]
for c in port_cuts:
    cob = cob.cut(c)
    door_part = door_part.cut(c)
cob = cob.clean()
door_part = door_part.clean()

# --- export ------------------------------------------------------------------------------------
cq.exporters.export(cq.Workplane().add(cob), str(HERE / "skycob_cob.step"))
cq.exporters.export(cq.Workplane().add(door_part), str(HERE / "skycob_door.step"))
cq.exporters.export(cq.Workplane().add(chassis), str(HERE / "cobby19mm_cam_stand_standoffs.step"))
if "--assembly" in sys.argv:  # large file, so only on request
    asm = cq.Assembly(name="skycob")
    asm.add(cob, name="cob", color=cq.Color(0.95, 0.8, 0.2))
    asm.add(chassis.translate(to_cob), name="chassis", color=cq.Color(0.6, 0.6, 0.6))
    asm.export(str(HERE / "skycob_assembly.step"))

bb = cob.BoundingBox()
print(f"stack envelope   {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm")
print(f"cavity           {cav_x:.1f} x {cav_y:.1f} x {cav_h:.1f} mm, flat ceiling")
print(f"cob              {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, core dia {2 * core_r:.1f} mm, "
      f"{len(kernels)} kernels, valid {cob.isValid()}, {cob.Volume() / 1000:.0f} cm^3")
print(f"chassis          valid {chassis.isValid()}, {chassis.Volume() / 1000:.1f} cm^3, "
      f"{len(chassis.Faces())} faces")
_v, _f = chassis.tessellate(0.08, 0.15)
_inv = np.unique(np.round([(p.x, p.y, p.z) for p in _v], 5), axis=0, return_inverse=True)[1].reshape(-1)
_f = _inv[np.array(_f)]
_e = np.sort(np.concatenate([_f[:, [0, 1]], _f[:, [1, 2]], _f[:, [2, 0]]]), axis=1)
_open = int((np.unique(_e, axis=0, return_counts=True)[1] != 2).sum())
print(f"chassis mesh     {_open} open/non-manifold edges when tessellated (slicers want 0)")
for x_edge, x_out, z0, z1 in side_rails:
    print(f"side rail        plate edge x={x_edge:.2f} built out to {x_out:.2f} mm, z {z0:.1f}..{z1:.1f}")
print("standoffs (chassis frame) " + ", ".join(f"({x:.2f}, {y:.2f})" for x, y in standoff_xy))
print(f"standoff span    {tx1 - tx0:.2f} x {ty1 - ty0:.2f} mm")
print("back peg holes (x, z) " + ", ".join(f"({b.center.x:.2f}, {b.center.z:.2f})" for b in back_pegs))
print(f"side holes       {SIDE_HOLE_DIA:.1f} mm at z={side_hole_z:.2f} mm, angles {SIDE_HOLE_ANGLES}")
print(f"RP-SMA port      {PORT_HOLE} mm hole at z={port_z:.2f} mm, {PORT_ANGLE:.0f} deg, "
      f"panel {spot_r - PORT_PANEL:.2f}..{spot_r:.2f} mm from axis")
dbb = door_part.BoundingBox()
print(f"door opening     {cav_x:.1f} mm wide, z 0..{door_z1:.1f} mm, +y wall")
print(f"door part        {dbb.xlen:.1f} x {dbb.ylen:.1f} x {dbb.zlen:.1f} mm, valid {door_part.isValid()}, "
      f"{door_part.Volume() / 1000:.0f} cm^3, {len(door_part.Solids())} solid(s)")
print("access bore depth " + ", ".join(f"{d:.0f}" for d in bore_depths) + " mm")
print(f"stack -> cob     translate by ({to_cob.x:.2f}, {to_cob.y:.2f}, {to_cob.z:.2f}) mm")
