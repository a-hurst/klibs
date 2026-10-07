__author__ = 'Jonathan Mulle & Austin Hurst'

import abc
from bisect import bisect
from os.path import join
from math import cos, sin, radians, ceil, sqrt

from aggdraw import Brush, Draw, Pen, Symbol
from PIL import Image
from numpy import asarray

from klibs.KLConstants import STROKE_CENTER, STROKE_INNER, STROKE_OUTER
from klibs import P
from klibs.KLInternal import iterable
from klibs.KLUtilities import point_pos, rotate_points, translate_points, canvas_size_from_points
from klibs.KLGraphics.utils import rgb_to_rgba, aggdraw_to_array
from klibs.KLGraphics.colorspaces import COLORSPACE_CONST


__all__ = [
    "drift_correct_target", "Stroke", "Drawbject",
    "Rectangle", "Ellipse", "Circle", "Triangle",  "Annulus", "Line", 
    "Arrow", "FixationCross", "Asterisk", "SquareAsterisk", "ColorWheel"
]


# Needed to avoid anti-aliasing weirdness on shapes without stroke
_null_stroke = Pen((0, 0, 0), 0, 0)


def cursor(color=None):
    dc =  Draw("RGBA", [32, 32], (0, 0, 0, 0))
    if color is not None:
        cursor_color = color[0:3]
    else:
        cursor_color = []
        for c in P.default_fill_color:
            cursor_color.append(abs(c - 255))
        cursor_color = cursor_color[0:3]
    # coordinate tuples are easier to read/modify but aggdraw needs a stupid x,y,x,y,x,y list
    cursor_coords = [(6, 0), (6, 27), (12, 21), (18, 32), (20, 30), (15, 20), (23, 20), (6, 0)]
    cursor_xy_list = []
    for point in cursor_coords:
        cursor_xy_list.append(point[0])
        cursor_xy_list.append(point[1])
    brush = Brush(tuple(cursor_color), 255)
    pen = Pen((255,255,255), 1, 255)
    dc.polygon(cursor_xy_list, pen, brush)
    cursor_surface = aggdraw_to_array(dc)
    return cursor_surface


def drift_correct_target():
    draw_context_length = P.screen_y // 60
    while draw_context_length % 3 != 0: # inner dot should be 1/3 size of target
        draw_context_length += 1
    black_brush = Brush((0, 0, 0, 255))
    white_brush = Brush((255, 255, 255, 255))
    draw_context = Draw("RGBA", [draw_context_length + 2, draw_context_length + 2], (0, 0, 0, 0))
    draw_context.ellipse([0, 0, draw_context_length, draw_context_length], black_brush)
    wd_top = draw_context_length // 3 # size of the inner white dot of the calibration point
    wd_bot = 2 * draw_context_length // 3
    draw_context.ellipse([wd_top, wd_top, wd_bot, wd_bot], white_brush)

    return aggdraw_to_array(draw_context)


class Stroke(object):
    """Defines the outline properties of a shape.

    A Stroke defines the color, width (thickness), and alignment for the outline of a
    shape. For example, to create an empty red square with a stroke width of 10 pixels,
    you would do the following::

        RED = (255, 0, 0)
        outline = Stroke(10, RED)
        rect = Rectangle(100, 100, stroke=outline)

    The alignment of the stroke determines whether the outline is along the outside
    of the shape ('outer'), the inside of the shape ('inner'), or centered along the
    edges of the shape ('center'). For example, if an outer-aligned stroke with a width
    of 10 is applied to a square with a width of 100, the width of the square inside
    the stroke will still be 100 and total width of the square will be 120. If the same
    stroke was inner-aligned (the default), the total width of the square would instead
    be 100 and the width of the inner square would be 80.

    The same Stroke can be reused for multiple shapes.

    Args:
        width (int): The thickness of the outline (in pixels).
        color (tuple): The color of the outline (as an RGB or RGBA list).
        align (str, optional): The alignment of the outline with the shape.
            Defaults to 'inner'.

    """
    def __init__(self, width, color, align='inner'):
        # Initialize parameters
        self._width = int(width)
        self._color = rgb_to_rgba(color)
        self._align = str(align).lower()
        # Validate parameter values
        if self._width <= 0:
            e = "Stroke width must be a positive integer (got '{0}')"
            raise ValueError(e.format(str(width)))
        if not self._align in ['outer', 'inner', 'center']:
            e = "Invalid stroke alignment '{0}'".format(align)
            raise ValueError(e)
        
        # Create actual Pen object
        self._pen = Pen(self._color[:3], self._width, self._color[3])

    @property
    def width(self):
        """int: The width of the stroke."""
        return self._width

    @property
    def color(self):
        """tuple: The RGBA color of the stroke."""
        return self._color

    @property
    def alignment(self):
        """str: The alignment of the stroke ('inner', 'outer', or 'center')."""
        return self._align


class Drawbject(object):
    """An abstract class that serves as the foundation for all KLDraw shapes. All Drawbjects
    are drawn on an internal surface using the aggdraw drawing library, which can then be drawn
    to the display buffer using blit() and displayed on the screen using flip(). For more
    infomration on drawing in KLibs, please refer to the guide in the documentation.

    Args:
        width (int): The width of the shape in pixels.
        height (int): The height of the shape in pixels.
        stroke (:obj:`Stroke`): The outline properties of the shape.
        fill (Tuple[color]): The fill color for the shape expressed as an iterable of integer 
            values from 0 to 255 representing an RGB or RGBA color (e.g. (255,0,0,128)
            for bright red with 50% transparency.)
        rotation (int|float, optional): The degrees by which to rotate the Drawbject during
            rendering. Defaults to 0.

    Attributes:
        object_width (int): The width of the shape in pixels.
        object_height (int): The height of the shape in pixels.
        surface (:obj:`aggdraw.Draw`): The aggdraw context on which the shape is drawn.
            When a shape is drawn to the surface, it is immediately applied to the canvas.
        canvas (:obj:`PIL.Image.Image`): The Image object that contains the shape of the
            Drawbject before opacity has been applied. Initialized upon creation with a
            size of (surface_width x surface_height).
        rendered (None or :obj:`numpy.array`): The rendered surface containing the shape,
            which is created using the render() method. If the Drawbject has not yet been
            rendered, this attribute will be 'None'.
        rotation (int): The rotation of the shape in degrees. Will be equal to 0 if no
            rotation is set.

    """

    def __init__(self, width, height, stroke, fill, rotation=0):

        self.surface = None
        self.canvas = None
        self.rendered = None

        self._stroke = None
        self.stroke = stroke

        self._fill = None
        self.fill_color = None
        self.fill = fill

        self._dimensions = None
        self.object_width = width
        self.object_height = height
        self.rotation = rotation

        self.render()


    def __str__(self):
        properties = [self.__name__, self.surface_width, self.surface_height, hex(id(self))]
        return "klibs.Drawbject.{0} ({1} x {2}) at {3}".format(*properties)

    def _init_surface(self):
        self._update_dimensions()
        self.rendered = None # Clear any existing rendered texture
        if self.fill_color:
            if self.stroke and self.fill_color[3] == 255:
                col = self.stroke.color
            else:
                col = self.fill_color
        elif self.stroke:
            col = self.stroke.color
        else:
            col = (0, 0, 0)
        self.canvas = Image.new("RGBA", self.dimensions, (col[0], col[1], col[2], 0))
        self.surface = Draw(self.canvas)
        self.surface.setantialias(True)

    def render(self):
        """Pre-renders the shape so it can be drawn to the screen using
        :func:`~klibs.KLGraphics.blit`. Although it is not necessary to pre-render
        shapes before drawing them to the screen, it will make the initial blit faster
        and is recommended wherever possible. 
        
        Once a Drawbject has been rendered, it will not need to be rendered again unless
        any of its properties (e.g. stroke, fill, rotation) are changed.
        
        Returns:
            :obj:`~numpy.ndarray`: A numpy array of the rendered shape.

        """
        self._init_surface()
        self.draw()
        self.rendered = asarray(self.canvas)
        return self.rendered

    def _update_dimensions(self):
        pts = self._draw_points(outline=True)
        if pts != None:
            self._dimensions = canvas_size_from_points(pts, flat=True)
        else:
            stroke_w = 0
            if self.stroke:
                if self.stroke.alignment == 'outer':
                    stroke_w = self.stroke.width * 2
                elif self.stroke.alignment == 'center':
                    stroke_w = self.stroke.width
            w, h = [self.object_width, self.object_height]
            self._dimensions = [int(ceil(w+stroke_w))+2, int(ceil(h+stroke_w))+2]

    @property
    def dimensions(self):
        """List[int, int]: The height and width of the internal surface on which the shape
        is drawn.
        """
        return self._dimensions

    @property
    def surface_width(self):
        """int: The width of the draw surface in pixels.
        
        At minimum two pixels wider than the object_width (if no stroke or stroke is
        inner aligned), at maximum (2 + 2 * stroke_width) pixels wider than object width
        (if stroke is outer aligned).

        """
        return self._dimensions[0]

    @property
    def surface_height(self):
        """int: The height of the draw surface in pixels.
        
        At minimum two pixels wider than the object_height (if no stroke or stroke is
        inner aligned), at maximum (2 + 2 * stroke_height) pixels wider than object
        height (if stroke is outer aligned).

        """
        return self._dimensions[1]

    @property
    def stroke(self):
        """:obj:`~Stroke` or None: The outline of the shape (or None if no outline).

        """
        return self._stroke

    @stroke.setter
    def stroke(self, style):
        # Parse provided stroke
        if not style:
            self._stroke = None
        elif isinstance(style, Stroke):
            self._stroke = style
        elif iterable(style) and len(style) in (2, 3):
            # [Compat]: for matching old API
            if len(style) == 3:
                const_map = {
                    STROKE_INNER: 'inner',
                    STROKE_OUTER: 'outer',
                    STROKE_CENTER: 'center',
                }
                width, color, align = style
                self._stroke = Stroke(width, color, const_map[align])
            elif len(style) == 2:
                width, color = style
                self._stroke = Stroke(width, color, 'outer')
        else:
            e = "Invalid stroke format '{0}'"
            raise ValueError(e.format(str(style)))

        # Re-initialize surface if it already exists
        if self.surface:
            self._init_surface()

    @property
    def stroke_offset(self):
        if self.stroke:
            if self.stroke.alignment == 'outer':
                return self.stroke.width * 0.5
            if self.stroke.alignment == 'inner':
                return self.stroke.width * -0.5
        return 0 

    @property
    def fill(self):
        """Tuple or None: The RGBA fill colour for the shape (or None if no fill).
        
        """
        return self.fill_color

    @fill.setter
    def fill(self, color):
        color = rgb_to_rgba(color) if color else None
        self.fill_color = color
        self._fill = Brush(color[:3], color[3]) if color else None
        # If shape already initialized, re-render
        if self.surface:
            self._init_surface()

    @abc.abstractmethod
    def _draw_points(self, outline=False):
        return None

    @abc.abstractmethod
    def draw(self):
        pts = self._draw_points()
        dx = self.surface_width / 2.0
        dy = self.surface_height / 2.0
        pts = translate_points(pts, delta=(dx, dy), flat=True)
        
        stroke = self.stroke._pen if self.stroke else _null_stroke
        self.surface.polygon(pts, stroke, self._fill)
        self.surface.flush()
        return self.canvas

    @abc.abstractproperty
    def __name__(self):
        pass


class FixationCross(Drawbject):
    """Creates a Drawbject containing a fixation cross.

    Args:
        size (int): The height and width of the cross in pixels.
        thickness (int): The thickness of the cross in pixels.
        stroke (:obj:`~Stroke`, optional): The outline properties of the cross.
            Defaults to None (no outline).
        fill (Tuple[color], optional): The fill color for the cross in RGB or RGBA format.
            Defaults to transparent fill.
        rotation (numeric, optional): The angle in degrees by which to rotate the cross 
            when rendered. Defaults to 0 (no rotation).

    """
    def __init__(self, size, thickness, stroke=None, fill=None, rotation=0):
        self.thickness = thickness
        super(FixationCross, self).__init__(size, size, stroke, fill, rotation)

    def _draw_points(self, outline=False):
        sw = self.stroke.width if self.stroke else 0
        so = self.stroke_offset + sw / 2.0 if outline else self.stroke_offset
        ht = self.thickness / 2.0 + so # half of the cross' thickness
        hs = self.object_width / 2.0 + so # half of the cross' size
        pts = []
        pts += [-hs, ht, -ht, ht, -ht, hs] # upper-left corner
        pts += [ht, hs, ht, ht, hs, ht] # upper-right corner
        pts += [hs, -ht, ht, -ht, ht, -hs] # lower-right corner
        pts += [-ht, -hs, -ht, -ht, -hs, -ht] # lower-left corner
        if self.rotation != 0:
            pts = rotate_points(pts, (0, 0), self.rotation, flat=True)
        return pts

    @property
    def __name__(self):
        return "FixationCross"


class Ellipse(Drawbject):
    """Creates a Drawbject containing an ellipse.

    Args:
        width (int): The width of the ellipse in pixels.
        height (int, optional): The height of the ellipse in pixels. Defaults to width.
        stroke (:obj:`~Stroke`, optional): The outline properties of the ellipse.
            Defaults to None (no outline).
        fill (Tuple[color], optional): The fill color for the ellipse in RGB or RGBA
            format. Defaults to transparent fill.

    """

    def __init__(self, width, height=None, stroke=None, fill=None):
        if not height:
            height = width
        super(Ellipse, self).__init__(width, height, stroke, fill)

    def draw(self):
        surf_c = self.surface_width / 2.0 # center of the drawing surface
        x1 = surf_c-(self.object_width/2.0 + self.stroke_offset)
        y1 = surf_c-(self.object_height/2.0 + self.stroke_offset)
        x2 = surf_c+(self.object_width/2.0 + self.stroke_offset)
        y2 = surf_c+(self.object_height/2.0 + self.stroke_offset)
        stroke = self.stroke._pen if self.stroke else None
        self.surface.ellipse([x1, y1, x2, y2], stroke, self._fill)
        self.surface.flush()
        return self.canvas

    @property
    def __name__(self):
        return "Ellipse"

    @property
    def width(self):
        """int: The width of the ellipse in pixels."""
        return self.object_width

    @width.setter
    def width(self, value):
        self.object_width = value
        self._init_surface()

    @property
    def height(self):
        """int: The height of the ellipse in pixels."""
        return self.object_height

    @height.setter
    def height(self, value):
        self.object_height = value
        self._init_surface()

    @property
    def diameter(self):
        """int or None: The diameter of the ellipse in pixels. If the height and width of
        the ellipse are not the same (i.e. if it is an oval and not a circle), this will
        return 'None'.

        """
        if self.object_width == self.object_height:
            return self.object_width
        else:
            return None

    @diameter.setter
    def diameter(self, value):
        self.object_height = value
        self.object_width = value
        self._init_surface()


class Circle(Ellipse):
    """Creates a Drawbject containing a circle. A special case of the Ellipse.

    Mainly here for backwards compatibility with older experiments, may be removed in a
    future release. You should probably use :obj:`~klibs.KLGraphics.KLDraw.Ellipse` instead
    of this.

    Args:
        diameter (int): The diameter of the circle in pixels.
        stroke (List[alignment, width, Tuple(color)], optional): The stroke of the circle,
            indicating the alignment (inner, center, or outer), width, and color of the
            stroke. Defaults to no stroke.
        fill (Tuple(color), optional): The fill color for the circle in RGB or RGBA
            format. Defaults to transparent fill.

    """

    def __init__(self, diameter, stroke=None, fill=None):
        super(Circle, self).__init__(diameter, diameter, stroke, fill)


class Annulus(Drawbject):
    """Creates a Drawbject containing an annulus.

    Args:
        diameter (int): The diameter of the annulus in pixels.
        thickness (int): The thickness of the ring of the annulus in pixels.
        stroke (:obj:`~Stroke`, optional): The outline properties of the annulus.
            Defaults to None (no outline).
        fill (Tuple[color], optional): The fill color for the annulus in RGB or RGBA
            format. Defaults to transparent fill.

    """

    def __init__(self, diameter, thickness, stroke=None, fill=None):
        if thickness > (diameter / 2.0):
            raise ValueError("Annulus thickness cannot exceed radius.")
        self.thickness = thickness
        self.diameter = diameter
        self.radius = self.diameter / 2.0
        super(Annulus, self).__init__(diameter, diameter, stroke, fill)

    def draw(self):
        surf_c = self.surface_width / 2.0 # center of the drawing surface
        stroke_w = self.stroke.width if self.stroke else 0
        stroke_col = tuple(self.stroke.color) if self.stroke else (0, 0, 0, 0)
        if self.stroke:
            if self.stroke.alignment == 'center':
                stroke_pen = Pen(stroke_col, stroke_w / 2.0)
                # draw outer stroke ring
                xy_1 = surf_c - (self.radius + stroke_w / 4.0)
                xy_2 = surf_c + (self.radius + stroke_w / 4.0)
                self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroke_pen)
                # draw inner stroke ring
                xy_1 = surf_c - (self.radius - (self.thickness + stroke_w / 4.0))
                xy_2 = surf_c + (self.radius - (self.thickness + stroke_w / 4.0))
                self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroke_pen)
            else:
                if self.stroke.alignment == 'outer':
                    xy_1 = surf_c - (self.radius + stroke_w / 2.0)
                    xy_2 = surf_c + (self.radius + stroke_w / 2.0)
                elif self.stroke.alignment == 'inner':
                    xy_1 = surf_c - (self.radius - (self.thickness + stroke_w / 2.0))
                    xy_2 = surf_c + (self.radius - (self.thickness + stroke_w / 2.0))
                stroke_pen = Pen(stroke_col, stroke_w)
                self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroke_pen)
        if self.fill:
            xy_1 = surf_c - (self.radius - self.thickness / 2.0)
            xy_2 = surf_c + (self.radius - self.thickness / 2.0)
            ring_pen = Pen(self.fill, self.thickness)
            self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], ring_pen)
        self.surface.flush()
        return self.canvas

    @property
    def __name__(self):
        return "Annulus"


class Rectangle(Drawbject):
    """Creates a Drawbject containing a rectangle.

    Args:
        width (int): The width of the rectangle in pixels.
        height (int, optional): The height of the rectangle in pixels. Defaults to width.
        stroke (:obj:`~Stroke`, optional): The outline properties of the rectangle.
            Defaults to None (no outline).
        fill (Tuple[color], optional): The fill color for the rectangle in RGB or RGBA
            format. Defaults to transparent fill.
        rotation (numeric, optional): The angle in degrees by which to rotate the rectangle
            when rendered. Defaults to 0 (no rotation).

    """

    def __init__(self, width, height=None, stroke=None, fill=None, rotation=0):
        if not height:
            height = width
        super(Rectangle, self).__init__(width, height, stroke, fill, rotation)
    
    def _draw_points(self, outline=False):
        sw = self.stroke.width if self.stroke else 0
        so = self.stroke_offset + sw / 2.0 if outline else self.stroke_offset
        x1 = -(self.object_width/2.0 + so)
        y1 = -(self.object_height/2.0 + so)
        x2 = (self.object_width/2.0 + so)
        y2 = (self.object_height/2.0 + so)
        pts = [x1, y1, x2, y1, x2, y2, x1, y2]
        if self.rotation != 0:
            pts = rotate_points(pts, (0, 0), self.rotation, flat=True)
        return pts

    @property
    def __name__(self):
        return "Rectangle"


class Asterisk(Drawbject):
    """Creates a Drawbject containing an asterisk.

    Args:
        size (int): The height and width of the asterisk in pixels.
        fill (Tuple[color]): The color of the asterisk, expressed as an iterable of
            integer values from 0 to 255 representing an RGB or RGBA color.
        thickness (int, optional): The thickness of the asterisk in pixels. Defaults to '1'
            if no value is given.
        rotation (numeric, optional): The angle in degrees by which to rotate the asterisk 
            when rendered. Defaults to 0 (no rotation).

    """
    def __init__(self, size, thickness, fill, spokes=6, rotation=0):
        if spokes not in range(3, 13):
            raise ValueError("Number of spokes must be between 3 and 12.")
        self.size = size
        self.thickness = thickness
        self.spokes = spokes
        super(Asterisk, self).__init__(size, size, None, fill, rotation)

    def _draw_points(self, outline=False):
        ht = self.thickness / 2.0 # half of the asterisk's thickness
        hs = self.size / 2.0 # half of the asterisk's size
        pts = []
        for s in range(0, self.spokes):
            spoke = [-ht, -ht, -ht, -hs, ht, -hs, ht, -ht]
            pts += rotate_points(spoke, (0, 0), s*(360.0/self.spokes), flat=True)
        if self.rotation != 0:
            pts = rotate_points(pts, (0, 0), self.rotation, flat=True)
        return pts

    @property
    def __name__(self):
        return "Asterisk"


class SquareAsterisk(Drawbject):
    """Creates a Drawbject containing an eight-spoke square-shaped asterisk. Spokes alternate
    between short with flat ends and long with pointed ends.

    Args:
        size (int): The height and width of the asterisk in pixels.
        fill (Tuple[color]): The color of the asterisk, expressed as an iterable of
            integer values from 0 to 255 representing an RGB or RGBA color.
        thickness (int, optional): The thickness of the asterisk in pixels. Defaults to '1'
            if no value is given.
        rotation (numeric, optional): The angle in degrees by which to rotate the asterisk 
            when rendered. Defaults to 0 (no rotation).

    """
    def __init__(self, size, thickness, fill, rotation=0):
        self.size = size
        self.thickness = thickness
        super(SquareAsterisk, self).__init__(size, size, None, fill, rotation)
    
    def _draw_points(self, outline=False):
        ht = self.thickness / 2.0 # half of the asterisk's thickness
        hss = self.size / 2.0 # half of the asterisk's straight (vertical/horizontal) size
        hds = sqrt(2*(hss**2)) # half of the asterisk's diagonal size
        spokes = 8
        pts = []
        for s in range(0, spokes):
            if s%2 == 0: # alternate between short/flat and long/pointed spokes
                spoke = [-ht, ht, -ht, hss, ht, hss, ht, ht]
            else:
                spoke = [-ht, ht, -ht, hds-ht, 0, hds, ht, hds-ht, ht, ht]
            pts += rotate_points(spoke, (0, 0), s*(-360.0/spokes), flat=True)
        if self.rotation != 0:
            pts = rotate_points(pts, (0, 0), self.rotation, flat=True)
        return pts

    @property
    def __name__(self):
        return "SquareAsterisk"


class Line(Drawbject): # Now that Rectangle Drawbjects can be rotated, is this still useful?
    """Creates a Drawbject containing a line.

    Args:
        length (int): The length of the line in pixels.
        color (Tuple[color]): The color of the line, expressed as an iterable of
            integer values from 0 to 255 representing an RGB or RGBA color.
        thickness (int): The thickness of the line in pixels.
        rotation (int, optional): The degrees by which the line should be rotated. Defaults
            to 0 (vertical).
        pts(List[Tuple[x1,y1],Tuple[x2,y2]], optional): A pair of x,y pixel coordinates
            indicating where the line should be drawn between. Note that this still creates
            a surface just large enough to contain the line, so you will still need to blit
            your line in the proper location if you want to draw a line between two
            specific points on the screen.

    """

    def __init__(self, length, color, thickness, rotation=0, pts=None):
        if pts:
            self.p1, self.p2 = pts
        else:
            self.p1 = (0,0)
            self.p2 = point_pos(self.p1, length, -90, rotation) # rotation of 0 = vertical line

        self._translate_to_positive()
        # determine surface margins based on the rotation and thickness of the line so it doesn't
        # get cropped at the corners
        margin = point_pos((0,0), thickness/2.0, -90, rotation)
        self.margin = tuple([abs(i) for i in margin])
        w = abs(self.p1[0] - self.p2[0]) + self.margin[1] * 2
        h = abs(self.p1[1] - self.p2[1]) + self.margin[0] * 2
        super(Line, self).__init__(w, h, [thickness, color, STROKE_INNER], fill=None)

    def _translate_to_positive(self):
        """Translates line coordinates into aggdraw space (i.e. top-left corner becomes (0,0)) 
        by offsetting the coordinates such that the furthest left point is aligned to x=0 and
        the furthest up point is aligned to y=0.
        """
        x_offset = -min(self.p1[0], self.p2[0])
        y_offset = -min(self.p1[1], self.p2[1])
        self.p1 = (self.p1[0] + x_offset, self.p1[1] + y_offset)
        self.p2 = (self.p2[0] + x_offset, self.p2[1] + y_offset)

    def draw(self):
        x1 = self.p1[0] + (self.margin[1] + 1)
        y1 = self.p1[1] + (self.margin[0] + 1)
        x2 = self.p2[0] + (self.margin[1] + 1)
        y2 = self.p2[1] + (self.margin[0] + 1)
        self.surface.line((x1, y2, x2, y1), self.stroke._pen)
        self.surface.flush()
        return self.canvas

    @property
    def __name__(self):
        return "Line"


class Triangle(Drawbject):
    """Creates a Drawbject containing an isoceles or equilateral triangle.

    Args:
        base (int): The width of the base of the triangle in pixels.
        height (int, optional): The height of the triangle in pixels. If not specified,
            an equilateral triangle will be drawn.
        rotation (float|int, optional): The degrees by which to rotate the triangle when
            rendering. Defaults to 0 (no rotation).
        stroke (:obj:`~Stroke`, optional): The outline properties of the triangle.
            Defaults to None (no outline).
        fill (Tuple[color], optional): The fill color for the triangle in RGB or RGBA format.
            Defaults to transparent fill.
        rotation (numeric, optional): The angle in degrees by which to rotate the triangle
            when rendered. Defaults to 0 (no rotation).

    """
    def __init__(self, base, height=None, stroke=None, fill=None, rotation=0):
        self.base = base
        if not height: # if no height given, draw equilateral
            height = base/2.0 * sqrt(3)
        self.height = height
        super(Triangle, self).__init__(base, height, stroke, fill, rotation)
    
    def _draw_points(self, outline=False):
        sw = self.stroke.width if self.stroke else 0
        so = self.stroke_offset + sw / 2.0 if outline else self.stroke_offset
        half_y = self.height / 2.0 + so
        half_x = (half_y*2)/(self.height/(self.base/2.0)) # to preserve angles when adding stroke
        pts = [-half_x, half_y, 0, -half_y, half_x, half_y]
        if self.rotation != 0:
            pts = rotate_points(pts, (0, 0), self.rotation, flat=True)
        return pts

    @property
    def __name__(self):
        return "Triangle"


class Arrow(Drawbject):
    """Creates a Drawbject containing an arrow.

    Note that research on arrows as spatial cues suggests that arrows are followed 
    reflexively to an extent, so if you are looking to use an arrow in your experiment
    as a truly endogenous cue you may want to consider a more neutral cue stimulus instead
    (e.g. squares and diamonds).

    Args:
        tail_w (int): The width of the tail of the arrow in pixels.
        tail_h (int): The height of the tail of the arrow in pixels.
        head_w (int): The width of the head of the arrow in pixels.
        head_h (int): The height of the head of the arrow in pixels.
        rotation (int, optional): The degrees by which to rotate the arrow when
            rendered. Defaults to 0 (no rotation).
        stroke (:obj:`~Stroke`, optional): The outline properties of the arrow. Defaults
            to None (no outline).
        fill (Tuple[color], optional): The fill color for the arrow in RGB or RGBA format.
            Defaults to transparent fill.

    """
    def __init__(self, tail_w, tail_h, head_w, head_h, rotation=0, stroke=None, fill=None):
        self.tail_w = tail_w
        self.tail_h = tail_h
        self.head_h = head_h
        self.head_w = head_w
        arrow_w = self.head_w + self.tail_w
        arrow_h = self.head_h if head_h > tail_h else tail_h
        super(Arrow, self).__init__(arrow_w, arrow_h, stroke, fill, rotation)
    
    def _draw_points(self, outline=False):
        sw = self.stroke.width if self.stroke else 0
        so = self.stroke_offset + sw / 2.0 if outline else self.stroke_offset
        xo = -(self.tail_w + self.head_w) / 2.0 - so # starting x value (x origin)
        half_hh = (self.head_w+2*so)/(self.head_w/(self.head_h/2.0)) # half head height
        pts = []
        # draw the tail
        pts += [xo + self.tail_w, self.tail_h / 2.0 + so]
        pts += [xo, self.tail_h / 2.0 + so]
        pts += [xo, -self.tail_h / 2.0 - so]
        pts += [xo + self.tail_w, -self.tail_h / 2.0 - so]
        # draw the head
        pts += [xo + self.tail_w, -half_hh]
        pts += [xo + self.tail_w + self.head_w + so*2, 0]
        pts += [xo + self.tail_w, half_hh]
        if self.rotation != 0:
            pts = rotate_points(pts, (0,0), self.rotation, flat=True)
        return pts

    @property
    def __name__(self):
        return "Arrow"


class ColorWheel(Drawbject):
    """Creates a Drawbject containing a color wheel. By default, the color wheel
    is constant-luminance.

    Args:
        diameter (int): The diameter of the color wheel in pixels.
        thickness (int, optional): The width of the ring of the color wheel in pixels.
            Defaults to one quarter of the diameter if not specified.
        colors (:obj:`list`, optional): The list of colours to render the colour
            wheel with, in the form of RGB or RGBA tuples. Defaults to a CIELUV
            constant-luminance colour wheel if not specified.
        rotation (int, optional): The angle in degrees by which to rotate the color wheel
            when rendered. Defaults to 0 (no rotation).
        
    """

    def __init__(self, diameter, thickness=None, colors=None, rotation=0):
        if colors == None:
            colors = COLORSPACE_CONST
        self._colors = [rgb_to_rgba(tuple(c)) for c in colors]
        self.diameter = diameter
        self.radius = self.diameter / 2.0
        self.thickness = 0.20 * diameter if not thickness else thickness
        super(ColorWheel, self).__init__(diameter, diameter, None, None, rotation)

    def draw(self):
        rotation = self.rotation
        center = self.surface_width / 2.0
        r = self.radius + 1
        for i in range(0, len(self.colors)):
            brush = Brush(rgb_to_rgba(self.colors[i]))
            vertices = [center, center]
            for i in range(0, 4):
                r_shift = -0.25 if i < 2 else 1.25
                r_shift -= rotation
                func = cos if i % 2 else sin
                vertices.append(r + r * func(radians(r_shift + 180)))
            self.surface.polygon(vertices, brush)
            rotation += 360.0 / len(self.colors)
        self.surface.flush()

        # Create annulus mask and apply it to colour disc
        mask = Image.new('L', (self.surface_width, self.surface_height), 0)
        d = Draw(mask)
        xy_1 = center - (self.radius-self.thickness / 2.0)
        xy_2 = center + (self.radius-self.thickness / 2.0)
        path_pen = Pen(255, self.thickness)
        d.ellipse([xy_1, xy_1, xy_2, xy_2], path_pen)
        d.flush()
        self.canvas.putalpha(mask)

        return self.canvas

    def color_from_angle(self, angle, rotation=None):
        """Retrieves the color at a given angle on the wheel, taking any rotation into account.
        """
        if not rotation:
            rotation = self.rotation
        
        degrees_per_colour = 360.0 / len(self.colors)
        adj_angle = (angle - rotation) % 360
        i = int(adj_angle / degrees_per_colour)
        color = self.colors[i]
        return color

    def angle_from_color(self, color, rotation=None):
        """Retreives the angle of the middle of a given color on the wheel, taking any rotation
        into account.
        """
        #TODO: return true middle when two or more adjacent colours are the same
        if not rotation:
            rotation = self.rotation

        try:
            i = self.colors.index(rgb_to_rgba(tuple(color)))
        except ValueError:
            err_str = "The color '{0}' does not exist in the color wheel palette."
            raise ValueError(err_str.format(rgb_to_rgba(color)))
        degrees_per_colour = 360.0 / len(self.colors)
        angle = ((i + 0.5) * degrees_per_colour + rotation) % 360
        return angle

    @property
    def colors(self):
        return self._colors

    @property
    def __name__(self):
        return "ColorWheel"
