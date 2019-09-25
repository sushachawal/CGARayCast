from clifford.tools.g3c import *
from clifford.tools.g3c.GAOnline import *

from pyganja import *

import numpy as np
from PIL import Image
import time
from scipy.optimize import fsolve
import  scipy.interpolate

red = 'rgb(255, 0 , 0)'
blue = 'rgb(0, 0, 255)'
green = 'rgb(0,255, 0)'
yellow = 'rgb(255, 255, 0)'
magenta = 'rgb(255, 0, 255)'
cyan = 'rgb(0,255,255)'
black = 'rgb(0,0,0)'
dark_blue = 'rgb(8, 0, 84)'
db = [0.033, 0., 0.33]


@numba.njit
def nth_polynomial_fit(x, y, n):
    """
    Fits an nth order polynomial to x and y
    """
    xmat = np.zeros((n+1,n+1))
    for i in range(n+1):
        for j in range(n+1):
            xmat[i,j] = x[i]**((n-j))
    return np.linalg.solve(xmat, y)


@numba.njit
def quad(x, p):
    """
    Evaluates the quadratic p at x
    """
    return p[0]*x**2 + p[1]*x + p[2]


@numba.njit
def bisection(p, start, stop):
    """
    Bisects start -> stop looking for roots of qudratic p
    """
    fstart = quad(start, p)
    for __ in range(1000):
        half = start + (stop - start)/2
        fhalf = quad(half, p)
        if abs(fhalf) < 1e-12:
            return half 
        if fhalf * fstart > 0:
            start = half
            fstart = quad(start, p)
        else:
            stop = half
    return half


@numba.njit
def get_root(x, y):
    """
    Finds the root of y over the range of x
    """
    poly = nth_polynomial_fit(x, y, 2)
    return bisection(poly, x[0], x[2])


class Sphere:
    def __init__(self, c, r, colour, specular, spec_k, amb, diffuse, reflection):
        self.object = new_sphere(c + r*e1, c + r*e2, c + r*e3, c - r*e1)
        self.colour = np.array(colour)
        self.specular = specular
        self.spec_k = spec_k
        self.ambient = amb
        self.diffuse = diffuse
        self.reflection = reflection
        self.type = "Sphere"

    def getColour(self):
        return "rgb(%d, %d, %d)"% (int(self.colour[0]*255), int(self.colour[1]*255), int(self.colour[2]*255))

    def intersection_point(self, L, origin):
        """
        Given there is an intersection this returns the point of intersection
        """
        return pointofXsphere(L, self.object, origin), None

    def reflect_line(self, L, pX, alpha):
        """
        Given there is an intersection this reflects the line off the object
        """
        return -1.*reflect_in_sphere(L, self.object, pX)

    def as_scene(self):
        gs = GanjaScene()
        gs.add_object(self.object, color=rgb2hex((self.colour*255).astype(int)))
        return gs

class Plane:
    def __init__(self, p1, p2, p3, colour, specular, spec_k, amb, diffuse, reflection):
        self.object = new_plane(p1, p2, p3)
        self.colour = colour
        self.specular = specular
        self.spec_k = spec_k
        self.ambient = amb
        self.diffuse = diffuse
        self.reflection = reflection
        self.type = "Plane"

    def getColour(self):
        return "rgb(%d, %d, %d)" % (int(self.colour[0]*255), int(self.colour[1]*255), int(self.colour[2]*255))

    def intersection_point(self, L, origin):
        """
        Given there is an intersection this returns the point of intersection
        """
        return pointofXplane(L, self.object, origin), None

    def reflect_line(self, L, pX, alpha):
        """
        Given there is an intersection this reflects the line off the object
        """
        return layout.MultiVector(value=(gmt_func(gmt_func(self.object.value, L.value), self.object.value)))

    def as_scene(self):
        gs = GanjaScene()
        gs.add_object(self.object, color=rgb2hex((self.colour*255).astype(int)))
        return gs

class TriangularFacet(Plane):
    def __init__(self, p1, p2, p3, *args, **kwargs):
        self.A = up(p1)
        self.B = up(p2)
        self.C = up(p3)
        self.p1 = (self.A^self.C).normal()
        self.p2 = (self.A^self.B).normal()
        self.p3 = (self.C^self.B).normal()
        super().__init__(p1, p2, p3, *args, **kwargs)
        self.type = "Triangle"

    def does_line_hit(self, L):
        p1l = (self.p1^L)[31]
        p2l = (self.p2^L)[31]
        p3l = (self.p3^L)[31]
        alpha = p2l/(p2l-p1l)
        beta = p3l/(p3l-p2l)
        #
        return alpha <= 1 and alpha >=0 and beta <= 1 and beta >=0

    def intersection_point(self, L, origin):
        if self.does_line_hit(L):
            return pointofXplane(L, self.object, origin), None
        else:
            return np.array([-1.]), None

    def as_scene(self):
        gs = GanjaScene()
        gs.add_facet([self.A, self.B, self.C], color=rgb2hex((self.colour*255).astype(int)))
        return gs

class Circle:
    def __init__(self, p1, p2, p3, colour, specular, spec_k, amb, diffuse, reflection):
        self.object = -new_circle(p1, p2, p3)
        self.colour = colour
        self.specular = specular
        self.spec_k = spec_k
        self.ambient = amb
        self.diffuse = diffuse
        self.reflection = reflection
        self.type = "Circle"

    def getColour(self):
        return "rgb(%d, %d, %d)" % (int(self.colour[0]*255), int(self.colour[1]*255), int(self.colour[2]*255))

    def intersection_point(self, L, origin):
        """
        Given there is an intersection this returns the point of intersection
        """
        return pointofXcircle(L, self.object, origin), None

    def reflect_line(self, L, pX, alpha):
        """
        Given there is an intersection this reflects the line off the object
        """
        return layout.MultiVector(value=(gmt_func(gmt_func(val_normalised(
            omt_func(self.object.value, einf.value)), L.value),
            val_normalised(omt_func(self.object.value, einf.value)))))

    def as_scene(self):
        gs = GanjaScene()
        gs.add_object(self.object, color=rgb2hex((self.colour*255).astype(int)))
        return gs

class InterpSurface:
    def __init__(self, C1, C2, colour, specular, spec_k, amb, diffuse, reflection):
        self.first = C1
        self.second = C2
        self.colour = colour
        self.specular = specular
        self.spec_k = spec_k
        self.ambient = amb
        self.diffuse = diffuse
        self.reflection = reflection
        self.type = "Surface"
        self._probes = None
        self._probe_func = None
        self._intersection_func = None
        self._bounding_sphere = None
        self.probe_alphas = np.linspace(0,1,1000)

    def getColour(self):
        return "rgb(%d, %d, %d)" % (int(self.colour[0]*255), int(self.colour[1]*255), int(self.colour[2]*255))

    @property
    def bounding_sphere(self):
        """
        Gets an approximate bounding sphere around the surface to accelerate rendering

        This is specific per type of evolution object and hence needs overwriting
        """
        raise NotImplementedError('bounding_sphere has not been defined in the child class')

    @property
    def probe_func(self):
        """
        Gets the evolution paramater at points of intersection

        This is specific per type of evolution object and hence needs overwriting
        """
        raise NotImplementedError('probe_func has not been defined in the child class')

    def intersect_at_alpha(self, L, origin, alpha):
        """
        Given an intersection, return the point that is the intersection between
        the ray L and the surface at evolution parameter alpha

        This is specific per type of evolution object and hence needs overwriting
        """
        raise NotImplementedError('probe_func has not been defined in the child class')

    def reflect_line(self, L, pX, alpha):
        """
        Given there is an intersection this reflects the line off the object

        This is specific per type of evolution object and hence needs overwriting
        """
        pass

    @property
    def bound_func(self):
        sphere_val = self.bounding_sphere.value
        @numba.njit
        def bound_hit(ray_val):
            B = meet_val(ray_val, sphere_val)
            if gmt_func(B, B)[0] > 0.000001:
                return True
            else:
                return False
        return bound_hit

    @property
    def probes(self):
        if self._probes is None:
            self._probes = [interp_objects_root(self.first, self.second, alpha) for alpha in self.probe_alphas]
        return self._probes

    @property
    def intersection_func(self):
        if self._intersection_func is None:
            pfunc = self.probe_func
            palphas = self.probe_alphas
            bfunc = self.bound_func
            @numba.njit
            def intersect_line(Lval):
                """
                Evaluate the probes and get (up to 4) crossing points
                """
                alphas = -np.ones(4)
                if bfunc(Lval):
                    res = pfunc(Lval)
                    n = 0
                    m1 = np.sign(res[0])
                    for i in range(1,len(res)):
                        m2 = np.sign(res[i])
                        if m2 != m1: # The normal case is a change of sign
                            if i > 1:
                                alphas[n] = get_root(palphas[i-2:i+1],res[i-2:i+1])
                            else:
                                alphas[n] = get_root(palphas[i-1:i+2],res[i-1:i+2])
                            n = n + 1
                            if n > 3:
                                break
                        m1 = m2
                return alphas
            self._intersection_func = intersect_line
        return self._intersection_func

    def as_scene(self):
        gs = GanjaScene()
        nprobes = len(self.probes)
        for i in range(20):
            p = self.probes[int(i*nprobes/20)]
            gs.add_object(p, color=rgb2hex((self.colour*255).astype(int)))
        return gs

    def intersection_point(self, L, origin):
        """
        Given there is an intersection this returns the point of intersection and the
        evolution parameter at that point
        """

        # Find the intersection and select the ones within valid range
        alpha_vals = self.intersection_func(L.value)
        alpha_in_vals = [a for a in alpha_vals if a < 1 and a > 0]

        # Check if it misses entirely
        if len(alpha_in_vals) < 1:
            return np.array([-1.]), None

        # Calc the intersection points
        intersection_points = np.zeros((len(alpha_in_vals), 32))
        nskip = 0
        for i, alp in enumerate(alpha_in_vals):
            ptest = self.intersect_at_alpha(L, origin, alp)
            if self.test_point(ptest):
                intersection_points[i-nskip, :] = ptest
            else:
                nskip += 1
        intersection_points = intersection_points[0:len(alpha_in_vals)-nskip,:]
        if len(alpha_in_vals)-nskip == 0:
            return np.array([-1.]), None

        # Calc the closest intersection point to the origin
        closest_ind = int(np.argmax([imt_func(p, origin.value)[0] for p in intersection_points]))
        return intersection_points[closest_ind, :], alpha_in_vals[closest_ind]

    def test_point(self, ptest):
        return True


class CircleSurface(InterpSurface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def probe_func(self):
        """
        This generates a function that takes the meet squared and takes the scalar value of it
        """
        if self._probe_func is None:
            ntcmats = len(self.probes)
            pms = np.array([dual_func(p.value) for p in self.probes])
            @numba.njit
            def tcf(L):
                output = np.zeros(ntcmats)
                Lval = dual_func(L)
                for i in range(ntcmats):
                    val = omt_func(pms[i,:],Lval)
                    output[i] = imt_func(val,val)[0]
                return output
            self._probe_func = tcf
        return self._probe_func

    @property
    def bounding_sphere(self):
        """
        Finds an approximate bounding sphere for a set of circles
        """
        if self._bounding_sphere is None:
            self._bounding_sphere = enclosing_sphere([circle_to_sphere(C) for C in self.probes])
        return self._bounding_sphere

    def intersect_at_alpha(self, L, origin, alpha):
        """
        Given an intersection, return the point that is the intersection between
        the ray L and the surface at evolution parameter alpha

        This is specific per type of surface and hence needs overwriting
        """
        # For each alpha val make the plane associated with it
        interp_circle = my_interp_objects_root(self.first, self.second, alpha)
        plane1_val = val_normalised(omt_func(interp_circle.value, einf.value))

        # Check if the line lies in this plane
        if np.sum(np.abs(meet(interp_circle, L).value)) < 1E-3:
            # Intersect as it it were a sphere
            S = circle_to_sphere(interp_circle)
            return val_pointofXSphere(L.value, unsign_sphere(S).value, origin.value)
        else:
            return val_pointofXplane(L.value, plane1_val, origin.value)

    def get_analytic_normal(self, alpha, P):
        """
        Get the normal at of the surface at the point P that corresponds to alpha
        Via a closed form expression
        """
        dotC = val_differentiateLinearCircle(alpha, self.second.value, self.first.value)
        dotC = layout.MultiVector(value=dotC)
        C = my_interp_objects_root(self.first, self.second, alpha)
        omegaC = C * dotC
        dotP = P | omegaC
        LT = (dotP ^ P ^ einf)
        LC = ((C | P) ^ einf)
        normal = (LT * LC * I5)(3).normal()
        return normal

    def get_numerical_normal(self, alpha, P):
        """
        Get the normal at of the surface at the point P that corresponds to alpha
        Via numerical techniques
        """
        Aplus = my_interp_objects_root(self.first, self.second, alpha + 0.001)
        Aminus = my_interp_objects_root(self.first, self.second, alpha - 0.001)
        A = my_interp_objects_root(self.first, self.second, alpha)
        Pplus = project_points_to_circle([P], Aplus)[0]
        Pminus = project_points_to_circle([P], Aminus)[0]
        CA = (Pminus ^ P ^ Pplus)
        Tangent_CA = ((CA | P) ^ einf)
        Tangent_A = ((A | P) ^ einf)
        return -normalised((Tangent_A * Tangent_CA * I5)(3))

    def reflect_line(self, L, pX, alpha):
        """
        Reflects a line in the surface
        """
        normal = normalised(self.get_analytic_normal(alpha, pX))
        return normalised((-normal * L * normal)(3))


class PointPairSurface(InterpSurface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def probe_func(self):
        """
        This generates a function that takes the meet and takes the scalar value of it
        """
        if self._probe_func is None:
            ntcmats = len(self.probes)
            pms = np.array([p.value for p in self.probes])
            @numba.njit
            def tcf(L):
                output = np.zeros(ntcmats)
                #Lval = dual_func(L)
                for i in range(ntcmats):
                    output[i] = omt_func(pms[i,:],L)[31]
                return output
            self._probe_func = tcf
        return self._probe_func

    @property
    def bounding_sphere(self):
        """
        Finds an approximate bounding sphere for a set of circles
        """
        if self._bounding_sphere is None:
            self._bounding_sphere = unsign_sphere(self.first ^ self.second)
        return self._bounding_sphere

    def intersect_at_alpha(self, L, origin, alpha):
        """
        Given an intersection, return the point that is the intersection between
        the ray L and the surface at evolution parameter alpha

        This is specific per type of surface and hence needs overwriting
        """
        # For each alpha val make the plane associated with it
        interp_pp = my_interp_objects_root(self.first, self.second, alpha)
        ppl = normalised(interp_pp^einf)

        # Get the point
        point_val = midpoint_between_lines(L, ppl).value
       
        return point_val

    def get_numerical_normal(self, alpha, P):
        """
        Get the normal at of the surface at the point P that corresponds to alpha
        Via numerical techniques
        """
        Aplus = normalised(my_interp_objects_root(self.first, self.second, alpha + 0.001)^einf)
        Aminus = normalised(my_interp_objects_root(self.first, self.second, alpha - 0.001)^einf)
        A = my_interp_objects_root(self.first, self.second, alpha)
        Pplus = project_points_to_line([P], Aplus)[0]
        Pminus = project_points_to_line([P], Aminus)[0]
        CA = (Pminus ^ P ^ Pplus)
        Tangent_CA = ((CA | P) ^ einf)
        Tangent_A = normalised(A^einf)
        return -normalised((Tangent_A * Tangent_CA * I5)(3))

    def get_analytic_normal(self, alpha, P):
        """
        Get the normal at of the surface at the point P that corresponds to alpha
        Via a closed form expression
        """
        dotC = val_differentiateLinearPointPair(alpha, self.second.value, self.first.value)
        dotC = layout.MultiVector(value=dotC)
        C = my_interp_objects_root(self.first, self.second, alpha)
        omegaC = C * dotC
        dotP = P | omegaC
        LT = (dotP ^ P ^ einf)
        LC = (C^einf).normal()
        normal = (LT * LC * I5)(3).normal()
        return normal


    def reflect_line(self, L, pX, alpha):
        """
        Reflects a line in the surface
        """
        normal = normalised(self.get_analytic_normal(alpha, pX))
        return normalised((-normal * L * normal)(3))

    def test_point(self, ptest):
        if imt_func(ptest, dual_func(self.bounding_sphere.value))[0] > 0:
            return True
        else:
            return False


    # def intersection_point(self, L, origin):
    #     pX, alpha = super().intersection_point(L, origin)
    #     if imt_func(pX, self.bounding_sphere.value)[0] < 0:
    #         #print(imt_func(pX, self.bounding_sphere.value)[0], 'FAIL')
    #         pX[0] = -1.0
    #     return pX, alpha


class Light:
    def __init__(self, position, colour):
        self.position = position
        self.colour = colour
    def as_scene(self):
        gs = GanjaScene()
        gs.add_object((up(self.position) - 0.5*einf)*I5, color=Color.YELLOW)
        print((up(self.position) - 0.5*einf)*I5)
        return gs

def drawScene():
    Ptr = Ptl + 2*e1*xmax
    Pbl = Ptl - 2*e3*ymax
    Pbr = Ptr - 2*e3*ymax
    rect = [Ptl, Ptr, Pbr, Pbl]

    sc = GAScene()

    #Draw Camera transformation
    # sc.add_line(original, red)
    cam_c_line = (MVR*original*~MVR).normal()
    cam_pos = up(cam)
    sc.add_line(cam_c_line, red)
    sc.add_euc_point(cam_pos, blue)
    sc.add_euc_point(up(lookat), blue)

    #Draw screen corners
    scorners = [RMVR(up(pnt)) for pnt in rect]
    for scorn in scorners:
        sc.add_euc_point(scorn, cyan)

    #Draw screen rectangle

    top = new_point_pair(Ptl, Ptr)
    right = new_point_pair(Ptr, Pbr)
    bottom = new_point_pair(Pbr, Pbl)
    left = new_point_pair(Pbl, Ptl)
    diag = new_point_pair(Ptl, Pbr)
    sides = [top, right, bottom, left, diag]
    for side in sides:
        sc.add_point_pair(RMVR(side), dark_blue)

    tl = new_line(eo, Ptl)
    tr = new_line(eo, Ptr)
    bl = new_line(eo, Pbl)
    br = new_line(eo, Pbr)

    lines = [tl, tr, br, bl]
    for line in lines:
        sc.add_line(RMVR(line).normal(), dark_blue)
    for objects in scene:
        if objects.type == "Sphere":
            sc.add_sphere(objects.object, objects.getColour())
        elif objects.type == "Plane":
            sc.add_plane(objects.object, objects.getColour())
        elif objects.type == "Triangle":
            sc.add_point_pair(objects.p1, objects.getColour())
            sc.add_point_pair(objects.p2, objects.getColour())
            sc.add_point_pair(objects.p3, objects.getColour())
        elif objects.type == "Circle":
            sc.add_circle(objects.object, objects.getColour())
        else:
            col = objects.getColour()
            sc.add_point_pair(objects.first, col)
            sc.add_point_pair(objects.second, col)
            for circles in [interp_objects_root(objects.first, objects.second, alpha/100) for alpha in range(1,100,5)]:
                sc.add_point_pair(circles, col)

    for light in lights:
        l = light.position
        sc.add_euc_point(up(l), yellow)
        sc.add_sphere(new_sphere(l + e1, l+e2, l+e3, l-e1), yellow)

    print(sc)

    gs = GanjaScene()
    for s in scene:
        gs += s.as_scene()
    for l in lights:
        gs += l.as_scene()
    gs.add_object(cam_pos, color=Color.BLACK)
    gs.add_object(cam_c_line, color=Color.CYAN)
    gs.add_objects([RMVR(l) for l in lines], color=Color.BLUE)
    gs.add_objects(scorners, color=Color.BLACK)
    draw(gs, scale=0.1, browser_window=True)


def new_sphere(p1, p2, p3, p4):
    return unsign_sphere(normalised(up(p1) ^ up(p2) ^ up(p3) ^ up(p4)))


def new_circle(p1, p2, p3):
    return normalised(up(p1) ^ up(p2) ^ up(p3))


def new_plane(p1, p2, p3):
    return normalised(up(p1) ^ up(p2) ^ up(p3) ^ einf)


def new_line(p1, p2):
    return normalised(up(p1) ^ up(p2) ^ einf)


def new_point_pair(p1, p2):
    return normalised(up(p1) ^ up(p2))


def unsign_sphere(S):
    return normalised(S/(S.dual()|einf)[0])

@numba.njit
def val_unsign_sphere(S_val):
    return val_normalised(S_val / imt_func(dual_func(S_val), einf.value)[0])












@numba.njit
def val_pointofXSphere(ray_val, sphere_val, origin_val):
    B = meet_val(ray_val, sphere_val)
    if gmt_func(B,B)[0] > 0.000001:
        point_vals = val_point_pair_to_end_points(B)
        if imt_func(point_vals[0,:],origin_val)[0] > imt_func(point_vals[1,:],origin_val)[0]:
            return point_vals[0,:]
    output = np.zeros(32)
    output[0] = -1
    return output


def pointofXsphere(ray, sphere, origin):
    return val_pointofXSphere(ray.value, sphere.value, origin.value)


@numba.njit
def val_pointofXplane(ray_val, plane_val, origin_val):
    pX = val_intersect_line_and_plane_to_point(ray_val, plane_val)
    if pX[0] == -1.:
        return pX
    new_line1 = omt_func(origin_val, omt_func(pX, ninf_val))
    if abs((gmt_func(new_line1, new_line1))[0]) < 0.00001:
        return np.array([-1.])
    if imt_func(ray_val, val_normalised(new_line1))[0] > 0:
        return pX
    return np.array([-1.])


def pointofXplane(ray, plane, origin):
    return val_pointofXplane(ray.value, plane.value, origin.value)


def val_pointofXcircle(ray_val, circle_val, origin_val):
    m = meet_val(ray_val, circle_val)
    if (np.abs(m) <= 0.000001).all():
        return np.array([-1.])
    elif gmt_func(m, m)[0] <= 0.00001:
        return val_pointofXplane(ray_val, omt_func(circle_val, einf.value), origin_val)
    else:
        return np.array([-1.])


def pointofXcircle(ray, circle, origin):
    return val_pointofXcircle(ray.value, circle.value, origin.value)


def pointofXsurface(L, surf, origin):
    return surf.intersection_point(L, origin)


def cosangle_between_lines(l1, l2):
    return (l1 | l2)[0]


def getfattconf(inner_prod, a1, a2, a3):
    return min(1./(a1 + a2 * np.sqrt(-inner_prod) - a3*inner_prod), 1.)


def getfatt(d, a1, a2, a3):
    return min(1./(a1 + a2*d + a3*d*d), 1.)


def reflect_in_sphere(ray, sphere, pX):
    return normalised((pX|(sphere*ray*sphere))^einf)


@numba.njit
def val_interp_objects_root(C1_val, C2_val, alpha):
    C_temp = (1-alpha) * C1_val + alpha * C2_val
    return val_normalised(neg_twiddle_root_val(C_temp)[0])


def my_interp_objects_root(C1, C2, alpha):
    return layout.MultiVector(value=val_interp_objects_root(C1.value, C2.value, alpha))


@numba.njit
def val_differentiateLinearCircle(alpha, C1_val, C2_val):
    X_val = alpha*C1_val + (1-alpha) * C2_val

    phiSquared = -gmt_func(X_val, adjoint_func(X_val))
    phiSq0 = phiSquared[0]
    phiSq4 = project_val(phiSquared,4)

    dotz = C1_val - C2_val
    dotphiSq0 = 2*alpha*gmt_func(C1_val,C1_val)[0] - 2*(1-alpha)*gmt_func(C2_val,C2_val)[0] + (1-2*alpha)*(gmt_func(C1_val,C2_val)+gmt_func(C2_val,C1_val))[0]
    dotphiSq4 = (1-2*alpha) * project_val(gmt_func(C1_val,C2_val)+gmt_func(C2_val,C1_val), 4)

    tempsqrt = np.sqrt(phiSq0**2 -  gmt_func(phiSq4, phiSq4)[0])
    dott = (dotphiSq0 + ((phiSq0*dotphiSq0) - gmt_func(phiSq4, dotphiSq4) -gmt_func(dotphiSq4, phiSq4))/tempsqrt)[0]

    t = phiSq0 + tempsqrt
    sqrt2t = np.sqrt(2*t)

    f = t/(sqrt2t)
    dotf = (3*dott)/(2*sqrt2t)

    g = phiSq4/(sqrt2t)
    dotg = (4*t*dotphiSq4 - dott *phiSq4)/(2*t*sqrt2t)

    k = (f*f - gmt_func(g,g)[0])

    dotk = (2*f*dotf - gmt_func(g,dotg) - gmt_func(dotg, g))[0]

    fminusg = -g
    fminusg[0] += f
    dotfminusdotg = -dotg
    dotfminusdotg[0] += dotf
    term1 = k*gmt_func(dotz, fminusg)
    term2 = k*gmt_func(dotfminusdotg, X_val)
    term3 = -dotk*gmt_func(fminusg, X_val)
    Calphadot = val_normalised(project_val(term1 + term2 + term3, 3))

    return Calphadot


@numba.njit
def val_differentiateLinearPointPair(alpha, C1_val, C2_val):
    X_val = alpha*C1_val + (1-alpha) * C2_val

    phiSquared = -gmt_func(X_val, adjoint_func(X_val))
    phiSq0 = phiSquared[0]
    phiSq4 = project_val(phiSquared,4)

    dotz = C1_val - C2_val
    dotphiSq0 = 2*alpha*gmt_func(C1_val,C1_val)[0] - 2*(1-alpha)*gmt_func(C2_val,C2_val)[0] + (1-2*alpha)*(gmt_func(C1_val,C2_val)+gmt_func(C2_val,C1_val))[0]
    dotphiSq4 = (1-2*alpha) * project_val(gmt_func(C1_val,C2_val)+gmt_func(C2_val,C1_val), 4)

    tempsqrt = np.sqrt(phiSq0**2 -  gmt_func(phiSq4, phiSq4)[0])
    dott = (dotphiSq0 + ((phiSq0*dotphiSq0) - gmt_func(phiSq4, dotphiSq4) -gmt_func(dotphiSq4, phiSq4))/tempsqrt)[0]

    t = phiSq0 + tempsqrt
    sqrt2t = np.sqrt(2*t)

    f = t/(sqrt2t)
    dotf = (3*dott)/(2*sqrt2t)

    g = phiSq4/(sqrt2t)
    dotg = (4*t*dotphiSq4 - dott *phiSq4)/(2*t*sqrt2t)

    k = (f*f - gmt_func(g,g)[0])

    dotk = (2*f*dotf - gmt_func(g,dotg) - gmt_func(dotg, g))[0]

    fminusg = -g
    fminusg[0] += f
    dotfminusdotg = -dotg
    dotfminusdotg[0] += dotf
    term1 = k*gmt_func(dotz, fminusg)
    term2 = k*gmt_func(dotfminusdotg, X_val)
    term3 = -dotk*gmt_func(fminusg, X_val)
    Calphadot = val_normalised(project_val(term1 + term2 + term3, 2))

    return Calphadot

def intersects(ray, scene, origin):
    dist = -np.finfo(float).max
    index = None
    pXfin = None
    alpha = None
    alphaFin = None
    for idx, obj in enumerate(scene):
        pX, alpha = obj.intersection_point(ray, origin)
        if pX[0] < -0.5:
            continue
        if idx == 0:
            dist, index, pXfin, alphaFin = imt_func(pX, origin.value)[0] , idx , layout.MultiVector(value=pX), alpha
            continue
        t = imt_func(pX, origin.value)[0]
        if(t > dist):
            dist, index, pXfin, alphaFin = t, idx, layout.MultiVector(value=pX), alpha
    return pXfin, index, alphaFin


def trace_ray(ray, scene, origin, depth):

    # Initialise the pixel color
    pixel_col = np.zeros(3)

    # Check for intersections with the scene
    pX, index, alpha = intersects(ray, scene, origin)

    # If there is no intersection return the background color
    if index is None:
        return background
    # Otherwise get the object we have hit
    obj = scene[index]

    # Reflect the line in the object
    reflected = obj.reflect_line(ray, pX, alpha)
    # Get the normal
    norm = normalised(reflected - ray)

    # Iterate over the lights
    for light in lights:

        # Calculate the lighting model
        upl_val = val_up(light.position.value)
        toL = layout.MultiVector(value=val_normalised(omt_func(omt_func(pX.value, upl_val), einf.value)))
        d = layout.MultiVector(value=imt_func(pX.value, upl_val))[0]

        if options['ambient']:
            pixel_col += ambient * obj.ambient * obj.colour

        # Check for shadows
        Satt = 1.
        if intersects(toL, scene[:index] + scene[index + 1:], pX)[0] is not None:
            Satt *= 0.8

        fatt = getfattconf(d, a1, a2, a3)

        if options['specular']:
            pixel_col += Satt * fatt * obj.specular * \
                         max(cosangle_between_lines(norm, normalised(toL-ray)), 0) ** obj.spec_k * light.colour

        if options['diffuse']:
            pixel_col += Satt * fatt * obj.diffuse * max(cosangle_between_lines(norm, toL), 0) * obj.colour * light.colour

    if depth >= max_depth:
        return pixel_col
    pixel_col += obj.reflection * trace_ray(reflected, scene, pX, depth + 1) #/ ((depth + 1) ** 2)
    return pixel_col


def RMVR(mv):
    return apply_rotor(mv, MVR)

def render():
    img = np.zeros((h, w, 3))
    initial = RMVR(up(Ptl))
    clipped = 0
    start_time = time.time()
    for i in range(0, w):
        if i % 1 == 0:
            if i != 0:
                t_current = time.time() - start_time
                if t_current is not 0:
                    current_percent = (i/w * 100)
                    percent_per_second = current_percent/t_current
                    t_est_total = 100/percent_per_second
                    print(i/w * 100, "% complete", 
                        t_current/60 , 'mins elapsed',
                        (t_est_total - t_current)/60, ' mins remaining')
        point = initial
        line = normalised(upcam ^ initial ^ einf)
        for j in range(0, h):
            # print("Pixel coords are; %d, %d" % (j, i))
            value = trace_ray(line, scene, upcam, 0)
            new_value = np.clip(value, 0, 1)
            if np.any(value > 1.) or np.any(value < 0.):
                clipped += 1
            img[j, i, :] = new_value * 255.
            point = apply_rotor(point, dTy)
            line = normalised(upcam ^ point ^ einf)

        initial = apply_rotor(initial, dTx)
    # print("Total number of pixels clipped = %d" % clipped)
    return img


















if __name__ == "__main__":


    """
    Render a random scene
    """
    # Light position and color.
    lights = []
    L = -30. * e1 + 5. * e3 - 30. * e2
    colour_light = np.ones(3)
    lights.append(Light(L, colour_light))
    L = 30. * e1 + 5. * e3 - 30. * e2
    lights.append(Light(L, colour_light))

    # Shading options
    a1 = 0.02
    a2 = 0.0
    a3 = 0.002
    w = 600
    h = 480
    options = {'ambient': True, 'specular': True, 'diffuse': True}
    ambient = 0.3
    k = 1.  # Magic constant to scale everything by the same amount!
    max_depth = 2 # Maximum number of ray bounces

    background = np.zeros(3)  # [66./520., 185./510., 244./510.]

    # Add objects to the scene:
    scene = []
    D1 = generate_dilation_rotor(0.5)
    C1 = normalised(D1*random_point_pair()*~D1)
    C2 = normalised(D1*random_point_pair()*~D1)
    scene.append(
        PointPairSurface(C2, C1, np.array([0., 0., 1.]), k * 1., 100., k * .5, k * 1., k * 0.)
    )

    # Camera definitions
    cam = -25. * e2 + 1. * e1 + 5.5 * e3
    lookat = e1 + 5.5 * e3
    upcam = up(cam)
    f = 1.
    xmax = 1.0
    ymax = xmax * (h * 1.0 / w)




    start_time = time.time()

    # Get all of the required initial transformations
    optic_axis = new_line(cam, lookat)
    original = new_line(eo, e2)
    MVR = generate_translation_rotor(cam - lookat) * rotor_between_lines(original, optic_axis)
    dTx = MVR * generate_translation_rotor((2 * xmax / (w - 1)) * e1) * ~MVR
    dTy = MVR * generate_translation_rotor(-(2 * ymax / (h - 1)) * e3) * ~MVR

    Ptl = f * 1.0 * e2 - e1 * xmax + e3 * ymax

    # print('\n\n\n\nRENDERING THIS \n\n\n\n')
    # drawScene()
    # print('\n\n\n\n^ RENDERING THIS ^ \n\n\n\n')

    # imrendered = render()
    # print('MAX PIX: ', np.max(np.max(np.max(imrendered))))
    # print('MIN PIX: ', np.min(np.min(np.min(imrendered))))
    # im1 = Image.fromarray(imrendered.astype('uint8'), 'RGB')
    # im1.save('randomSurface.png')

    # print("\n\n")
    # print("--- %s seconds ---" % (time.time() - start_time))




    """
    Now render a fixed scene
    """
    start_time = time.time()

    lights = []
    L = -20. * e1 + 5. * e3 - 10. * e2
    colour_light = np.ones(3)
    lights.append(Light(L, colour_light))
    L = 20. * e1 + 5. * e3 - 10. * e2
    lights.append(Light(L, colour_light))

    cam = - 10. * e2 + 1. * e1
    lookat = e1
    upcam = up(cam)

    optic_axis = new_line(cam, lookat)
    original = new_line(eo, e2)
    MVR = generate_translation_rotor(cam - lookat) * rotor_between_lines(original, optic_axis)
    dTx = MVR * generate_translation_rotor((2 * xmax / (w - 1)) * e1) * ~MVR
    dTy = MVR * generate_translation_rotor(-(2 * ymax / (h - 1)) * e3) * ~MVR

    Ptl = f * 1.0 * e2 - e1 * xmax + e3 * ymax


    C1 = normalised(up(5*e2 + -10 *e1 - 4 * e3) ^ up(5*e2 + -10 *e1 + 4 * e2))
    C2 = normalised(up(4*e2 + 10 * e1 - 3 * e3) ^ up(5*e2 + 10 * e1 + 5 * e3))

    scene = []
    scene.append(
        PointPairSurface(C2, C1, np.array([0., 0., 1.]), k * 1., 100., k * .5, k * 1., k * 0.)
    )

    print('\n\n\n\nRENDERING THIS \n\n\n\n')
    drawScene()
    exit()
    print('\n\n\n\n^ RENDERING THIS ^ \n\n\n\n')

    im1 = Image.fromarray(render().astype('uint8'), 'RGB')
    im1.save('standardPointPairScene.png')

    print("\n\n")
    print("--- %s seconds ---" % (time.time() - start_time))



    # p1 = 5*e2 + -10 *e1 - 4 * e3
    # p2 = 5*e2 + -10 *e1 + 4 * e2
    # p3 = 4*e2 + 10 * e1 - 3 * e3
    # scene = []
    # scene.append(
    #     TriangularFacet(p1,p2,p3 , np.array([0., 0., 1.]), k * 1., 100., k * .5, k * 1., k * 0.)
    # )

    # print('\n\n\n\nRENDERING THIS \n\n\n\n')
    # drawScene()
    # print('\n\n\n\n^ RENDERING THIS ^ \n\n\n\n')

    # im1 = Image.fromarray(render().astype('uint8'), 'RGB')
    # im1.save('triangleScene.png')

    # print("\n\n")
    # print("--- %s seconds ---" % (time.time() - start_time))