__author__ = 'jono'

import abc
from aggdraw import Brush, Draw, Pen, Symbol
from PIL.Image import frombytes
from imp import load_source
from bisect import bisect
from os.path import join
from numpy import asarray
from math import cos, sin, radians

from klibs.KLConstants import STROKE_CENTER, STROKE_INNER, STROKE_OUTER, KLD_LINE, KLD_MOVE, KLD_ARC, KLD_PATH
from klibs import P
from klibs.KLUtilities import point_pos, midpoint

from klibs.KLGraphics.KLNumpySurface import NumpySurface as NpS


######################################################################
#
# aggdraw Documentation: http://effbot.org/zone/pythondoc-aggdraw.htm
#
######################################################################


def cursor(color=None):
	dc =  Draw("RGBA", [32, 32], (0, 0, 0, 0))
	if color is not None:
		cursor_color = color[0:3]
	else:
		cursor_color = []
		for c in P.default_fill_color:
			cursor_color.append(abs(c - 255))
		cursor_color = cursor_color[0:3]
	# coordinate tuples are easier to read/modify but aggdraw needs a stupid x,y,x,y,x,y list, so... :S
	cursor_coords = [(6, 0), (6, 27), (12, 21), (18, 32), (20, 30), (15, 20), (23, 20), (6, 0)]
	cursor_xy_list = []
	for point in cursor_coords:
		cursor_xy_list.append(point[0])
		cursor_xy_list.append(point[1])
	brush = Brush(tuple(cursor_color), 255)
	pen = Pen((255,255,255), 1, 255)
	dc.polygon(cursor_xy_list, pen, brush)
	cursor_surface = aggdraw_to_numpy_surface(dc)
	return cursor_surface


def drift_correct_target():
	from klibs.KLGraphics import aggdraw_to_numpy_surface
	draw_context_length = P.screen_y // 60
	while draw_context_length % 3 != 0:  # center-dot is 1/3 of parent; offset unequal if parent not divisible by 3
		draw_context_length += 1
	black_brush = Brush((0, 0, 0, 255))
	white_brush = Brush((255, 255, 255, 255))
	draw_context = Draw("RGBA", [draw_context_length + 2, draw_context_length + 2], (0, 0, 0, 0))
	draw_context.ellipse([0, 0, draw_context_length, draw_context_length], black_brush)
	wd_top = draw_context_length // 3  #ie. white_dot_top, the inner white dot of the calibration point
	wd_bot = 2 * draw_context_length // 3
	draw_context.ellipse([wd_top, wd_top, wd_bot, wd_bot], white_brush)

	return aggdraw_to_numpy_surface(draw_context)

colors = load_source("*", join(P.klibs_dir, "color_wheel_color_list.py")).colors


class Drawbject(object):
	"""An abstract class that serves as the foundation for all KLDraw shapes. All Drawbjects
	are drawn on an internal surface using the aggdraw drawing library, which can then be drawn
	to the display buffer using blit() and displayed on the screen using flip(). For more
	infomration on drawing in KLibs, please refer to the guide in the documentation.

	Args:
		width (int): The width of the shape in pixels.
		height (int): The height of the shape in pixels.
		stroke (List[alignment, width, Tuple[color]]): The stroke of the shape, indicating
			the alignment (inner, center, or outer), width, and color of the stroke.
		fill (Tuple[color]): The fill color for the shape expressed as an iterable of integer 
			values from 0 to 255 representing an RGB or RGBA color (e.g. (255,0,0,128)
			for bright red with 50% transparency.)
		rotation (int|float, optional): The degrees by which to rotate the Drawbject during
			rendering. Defaults to 0.

	Attributes:
		stroke_color (None or Tuple[color]): The stroke color for the shape, expressed as an
			iterable of integer values from 0 to 255 representing an RGB or RGBA color.
			Defaults to 'None' if the shape has no stroke.
		stroke_width (int): The stroke width for the in pixels. Defaults to '0' if the
			shape has no stroke.
		stroke_alignment (int): The stroke alignment for the shape (inner, center, or
			outer). Defaults to '1' (STROKE_INNER) if the shape has no stroke.
		fill_color (None or Tuple[color]): The fill color for the shape, expressed as an
			iterable of integer values from 0 to 255 representing an RGB or RGBA color.
			Defaults to 'None' if the shape has no fill.
		opacity (int): The opacity of the shape, expressed as an integer from 0 (fully
			transparent) to 255 (fully opaque).
		object_width (int): The width of the shape in pixels.
		object_height (int): The height of the shape in pixels.
		surface_width (int): The width of the draw surface in pixels. At minimum two 
			pixels wider than the object_width (if no stroke or stroke is inner aligned),
			at maximum (2 + 2*stroke_width) pixels wider than object width (if stroke is
			outer aligned).
		surface_height (int): The height of the draw surface in pixels. At minimum two 
			pixels wider than the object_height (if no stroke or stroke is inner aligned),
			at maximum (2 + 2*stroke_height) pixels wider than object height (if stroke is
			outer aligned).
		surface (:obj:`aggdraw.Draw`): The aggdraw surface on which the shape is drawn. The
			empty surface of size (surface_width, surface_height) is initialized when a
			Drawbject is created.
		rendered (None or :obj:`numpy.array`): The rendered surface containing the shape,
			which is created using the render() method. If the Drawbject has not yet been
			rendered, this attribute will be 'None'.
		rotation (int): The rotation of the shape in degrees. Will be equal to 0 if no
			rotation is set.

	"""

	transparent_brush = Brush((255, 0, 0), 0)

	def __init__(self, width, height, stroke, fill, rotation=0):
		super(Drawbject, self).__init__()

		self.__stroke = None
		self.stroke_color = None
		self.stroke_width = 0
		self.stroke_alignment = STROKE_INNER
		self.__fill = None
		self.fill_color = None
		self.opacity = None
		self.object_width = width
		self.object_height = height
		self.surface_width = None
		self.surface_height = None
		self.surface = None
		self.rendered = None
		self.rotation = rotation
		try:
			iter(stroke)
			self.stroke = stroke
		except TypeError:
			self.stroke = None

		try:
			self.fill = fill
		except TypeError:
			self.fill = None


		self.init_surface(width, height)

	def __str__(self):
		return "klibs.Drawbject.{0} ({1} x {2}) at {3}".format(self.__name__, self.surface_width, self.surface_height, hex(id(self)))

	def init_surface(self, width=None, height=None):
		if width is not None and height is not None:  # initial call infers dimensions; subsequent calls for clearing the surface only
			if self.stroke_alignment == STROKE_OUTER:
				self.surface_width = width + 2 + self.stroke_width * 2
				self.surface_height = height + 2 + self.stroke_width * 2
			elif self.stroke_alignment == STROKE_CENTER:
				self.surface_width = width + 2 + self.stroke_width
				self.surface_height = height + 2 + self.stroke_width
			else:
				self.surface_width = width + 2
				self.surface_height = height + 2
		self.surface = Draw("RGBA", [self.surface_width, self.surface_height], (0, 0, 0, 0))
		self.surface.setantialias(True)

	def render(self):
		"""Renders the Drawbject to a numpy array so it can be drawn to the display buffer
		using KLGraphics.blit(). This method is called implicitly when an unrendered
		Drawbject is passed to blit(), so while rendering a Drawbject explicitly is not
		required, it does make the blitting process faster and is recommended whenever
		possible. 
		
		Once a Drawbject is rendered, a copy of the resulting array is saved within the
		object under the 'rendered' attribute which will be used by blit() if present. 
		Note that if you change any of the attributes of a Drawbject (e.g. stroke, fill,
		rotation) after it has been rendered, you will need to call this method again
		before those changes will take effect.
		
		Returns:
			:obj:`numpy.array`: A numpy array with the dimensions (surface_height, 
				surface_width) containing the pixels of the rendered Drawbject.

		"""
		from PIL.Image import BILINEAR
		self.init_surface()
		self.draw()
		try: # old aggdraw uses tostring()
			surface_bytes = frombytes(self.surface.mode, self.surface.size, self.surface.tostring()).rotate(self.rotation, BILINEAR, False)
		except AttributeError: # new aggdraw uses tobytes()
			surface_bytes = frombytes(self.surface.mode, self.surface.size, self.surface.tobytes()).rotate(self.rotation, BILINEAR, False)
		surface_array = asarray(surface_bytes)

		if self.opacity < 255: # Apply opacity (if not fully opaque) to whole Drawbject
			surface_array.setflags(write=1) # make RGBA values writeable
			for x in range(self.surface.size[0]):
				for y in range(self.surface.size[1]):
					surface_array[x][y][3] = int(surface_array[x][y][3] * self.opacity/255)

		self.rendered = NpS(surface_array).render()
		return self.rendered

	@abc.abstractproperty
	def __name__(self):
		pass

	@property
	def stroke(self):
		"""None or :obj:`aggdraw.Pen`: An aggdraw Pen object set to the specified stroke width
		and color, or None if the Drawbject has no stroke.

		Raises:
			ValueError: If an invalid stroke alignment value is passed to the stroke setter.
				Valid values are 1 (STROKE_INNER), 2 (STROKE_CENTER), or 3 (STROKE_OUTER).
				For the sake of clarity, it is recommended that you define stroke alignment
				using the variable names provided in KLConstants (in brackets above).

		"""
		return self.__stroke

	@stroke.setter
	def stroke(self, style):
		if not style:
			self.stroke_alignment = STROKE_OUTER
			self.stroke_width = 0
			self.stroke_color = None
			return self
		try:
			width, color, alignment = style
		except ValueError:
			width, color = style
			alignment = STROKE_OUTER

		if alignment in [STROKE_INNER, STROKE_CENTER, STROKE_OUTER]:
			self.stroke_alignment = alignment
		else:
			raise ValueError("Invalid value provided for stroke alignment; see KLConstants for accepted values")

		if len(color) == 4:
			self.opacity = color[3]
			color = [i for i in color[0:3]]
		else:
			color = [i for i in color]
			self.opacity = 255
		self.stroke_color = color
		self.stroke_width = width
		self.__stroke = Pen(tuple(color), width, 255)
		if self.surface: # don't call this when initializing the Drawbject for the first time
			self.init_surface()
		return self

	@property
	def fill(self):
		"""None or :obj:`aggdraw.Brush`: An aggdraw Brush object set to the specified fill
		color, or None if the Drawbject has no fill.
		
		"""
		return self.__fill

	@fill.setter
	def fill(self, color):
		if not color:
			self.fill_color = None
			return self
		if len(color) == 4:
			self.opacity = color[3] if type(color[3]) is int else int(color[3] * 255)
			color = tuple(color[0:3])
		else:
			color = tuple(color)
			self.opacity = 255
		self.fill_color = color
		self.__fill = Brush(color, 255)
		if self.surface: # don't call this when initializing the Drawbject for the first time
			self.init_surface()
		return self

	@abc.abstractmethod
	def draw(self, as_numpy_surface=False):
		pass

	@property
	def dimensions(self):
		"""List[int, int]: The height and width of the internal surface on which the shape
		is drawn.

		"""
		return [self.surface_width, self.surface_height]


class FixationCross(Drawbject):
	"""Creates a Drawbject containing a fixation cross.

	Args:
		size (int): The height and width of the cross in pixels.
		thickness (int): The thickness of the cross in pixels.
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the cross,
			indicating the alignment of the stroke (inner, center, or outer), the stroke
			width, and the color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the cross in RGB or RGBA format.
			Defaults to transparent fill.
		auto_draw (bool): If True, draws the shape internally when created.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified fixation cross.

	"""
	def __init__(self, size, thickness, stroke=None, fill=None, auto_draw=True):
		if not stroke:  # ie. "fill" will actually be the stroke of two lines as against two intersecting rects
			stroke = [thickness, fill]
			fill = None
		super(FixationCross, self).__init__(size, size, stroke, fill)
		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=False):
		if not self.fill:
			self.surface.line((self.surface_width // 2, 1, self.surface_width // 2, self.surface_width - 1), self.stroke)
			self.surface.line((1, self.surface_height // 2, self.surface_height - 1, self.surface_height // 2), self.stroke)
		else:
			str_h1 = self.surface_height // 2 - self.stroke_width // 2
			str_h2 = self.surface_height // 2 + self.stroke_width // 2
			self.surface.rectangle([1, str_h1, self.surface_width - 1, str_h2])
		return self

	@property
	def __name__(self):
		return "FixationCross"


class Ellipse(Drawbject):
	"""Creates a Drawbject containing an ellipse.

	Args:
		width (int): The width of the ellipse in pixels.
		height (int, optional): The height of the ellipse in pixels. Defaults to width.
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the ellipse,
			indicating the alignment (inner, center, or outer), width, and color of the
			stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the ellipse in RGB or RGBA
			format. Defaults to transparent fill.
		auto_draw (bool): If True, internally draws the ellipse on initialization.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified ellipse.

	"""

	def __init__(self, width, height=None, stroke=None, fill=None, auto_draw=True):
		if not height:
			height = width
		super(Ellipse, self).__init__(width, height, stroke, fill)
		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=False):
		xy_1 = (self.stroke_width // 2) + 1
		x_2 = self.surface_width - ((self.stroke_width // 2) + 1)
		y_2 = self.surface_height - ((self.stroke_width // 2) + 1)
		self.surface.ellipse([xy_1, xy_1, x_2, y_2], self.stroke, self.fill)
		return self

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
		self.init_surface()

	@property
	def height(self):
		"""int: The height of the ellipse in pixels."""
		return self.object_height


	@height.setter
	def height(self, value):
		self.object_height = value
		self.init_surface()

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
		self.init_surface()


class Annulus(Drawbject):
	"""Creates a Drawbject containing an annulus.

	Args:
		diameter (int): The diameter of the annulus in pixels.
		ring_width (int): The width of the ring of the annulus in pixels.
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the
			annulus, indicating the alignment (inner, center, or outer), width, and
			color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the annulus in RGB or RGBA
			format. Defaults to transparent fill.
		rotation (int, optional): 
		auto_draw (bool): If True, internally draws the annulus on initialization.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified annulus.

	"""

	def __init__(self, diameter, ring_width, stroke=None, fill=None, rotation=0, auto_draw=True):
		super(Annulus, self).__init__(diameter + 2, diameter + 2, stroke, fill)
		self.ring_width = ring_width
		self.diameter = diameter
		self.radius = self.diameter // 2
		self.rotation = rotation
		try:
			self.ring_inner_width = ring_width - 2 * stroke[0]
		except TypeError:
			self.ring_inner_width = ring_width
		if self.ring_width > self.radius:
			raise ValueError("Ring width of annulus larger than radius; decrease ring_width or increase diameter")
		if self.ring_inner_width < 1:
			raise ValueError("Annulus area subsumed by stroke; increase ring_width or decrease stroke size")
		if stroke is None:
			self.stroke_color = (0,0,0,0)
			self.stroke_width = 0
		if auto_draw:
			self.draw()

	def draw(self,  as_numpy_surface=False):
		if self.stroke:
			stroked_path_pen = Pen(tuple(self.stroke_color), self.ring_width)
			xy_1 = 2 + self.ring_width//2
			xy_2 = self.surface_width - (2 + self.ring_width//2)
			self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroked_path_pen, self.transparent_brush)
		xy_1 = 2 + self.ring_width//2
		xy_2 = self.surface_width - (2 + self.ring_width//2)
		path_pen = Pen(tuple(self.fill_color), self.ring_inner_width)
		self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], path_pen, self.transparent_brush)

		return self

	@property
	def __name__(self):
		return "Annulus"


class Rectangle(Drawbject):
	"""Creates a Drawbject containing a rectangle.

	Args:
		width (int): The width of the rectangle in pixels.
		height (int, optional): The height of the rectangle in pixels. Defaults to width.
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the
			rectangle, indicating the alignment (inner, center, or outer), width, and
			color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the rectangle in RGB or RGBA
			format. Defaults to transparent fill.
		auto_draw (bool): If True, internally draws the rectangle on initialization.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified rectangle.

	"""

	def __init__(self, width, height=None, stroke=None, fill=None, auto_draw=True):
		if not height:
			height = width
		super(Rectangle, self).__init__(width, height, stroke, fill)
		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=False):
		stroke_offset = self.stroke_width//2
		xy1 = stroke_offset + 1
		x2 = self.surface_width  - (stroke_offset + 1)
		y2 = self.surface_height - (stroke_offset + 1)
		if self.stroke:
			if self.fill:
				self.surface.rectangle((xy1, xy1, x2, y2), self.stroke, self.fill)
			else:
				self.surface.rectangle((xy1, xy1, x2, y2), self.stroke)
		else:
			self.surface.rectangle((1, 1, self.surface_width - 1, self.surface_height - 1), self.fill)

		return self

	@property
	def __name__(self):
		return "Rectangle"


class Asterisk(Drawbject):
	"""Creates a Drawbject containing a six-spoke asterisk.

	Args:
		size (int): The height and width of the asterisk in pixels.
		color (Tuple[color]): The color of the asterisk, expressed as an iterable of
			integer values from 0 to 255 representing an RGB or RGBA color.
		stroke (int, optional): The thickness of the asterisk in pixels. Defaults to '1'
			if no value is given.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified asterisk.

	"""
	def __init__(self, size, color, stroke=1):
		super(Asterisk, self).__init__(size, size, (stroke, color), fill=None)
		self.size = size


	def draw(self, as_numpy_surface=False):
		x_os = int(self.surface_width * 0.925)
		y_os = int(self.surface_height * 0.75)
		l1 = [x_os + 1, y_os + 1, self.surface_width - x_os + 1, self.surface_height - y_os + 1]
		l2 = [self.surface_width - x_os + 1, y_os + 1, x_os + 1, self.surface_height - y_os + 1]
		l3 = [self.surface_width // 2 + 1, 1, self.surface_width // 2 + 1, self.surface_height + 1]
		self.surface.line((l1[0], l1[1], l1[2],l1[3]), self.stroke)
		self.surface.line((l2[0], l2[1], l2[2],l2[3]), self.stroke)
		self.surface.line((l3[0], l3[1], l3[2],l3[3]), self.stroke)

		return self.surface

	@property
	def __name__(self):
		return "Asterisk"


class Asterisk2(Drawbject):
	"""Creates a Drawbject containing an eight-spoke asterisk.

	Args:
		size (int): The height and width of the asterisk in pixels.
		color (Tuple[color]): The color of the asterisk, expressed as an iterable of
			integer values from 0 to 255 representing an RGB or RGBA color.
		stroke (int, optional): The thickness of the asterisk in pixels. Defaults to '1'
			if no value is given.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified asterisk.

	"""
	def __init__(self, size, color, stroke=1):
		super(Asterisk2, self).__init__(size, size, (stroke, color), fill=None)
		self.size = size


	def draw(self, as_numpy_surface=False):
		l1 = [1, 1, self.surface_width + 1, self.surface_height + 1]
		l2 = [self.surface_width + 1, 1, 1, self.surface_height + 1]
		l3 = [self.surface_width // 2 + 1, 1, self.surface_width // 2 + 1, self.surface_height + 1]
		l4 = [1, self.surface_height // 2 + 1, self.surface_width + 1, self.surface_height // 2 + 1]
		self.surface.line((l1[0], l1[1], l1[2],l1[3]), self.stroke)
		self.surface.line((l2[0], l2[1], l2[2],l2[3]), self.stroke)
		self.surface.line((l3[0], l3[1], l3[2],l3[3]), self.stroke)
		self.surface.line((l4[0], l4[1], l4[2],l4[3]), self.stroke)

		return self.surface

	@property
	def __name__(self):
		return "Asterisk2"


class Line(Drawbject):
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
		auto_draw (bool): If True, internally draws the line on initialization.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified line.

	"""

	def __init__(self, length, color, thickness, rotation=0, pts=None, auto_draw=True):
		self.rotation = rotation
		if pts:
			self.p1, self.p2 = pts
		else:
			self.p1 = (0,0)
			self.p2 = point_pos(self.p1, length, -90, rotation) # A rotation of 0 draws a vertical line

		self.__translate_to_positive__()
		# determine surface margins depending on the rotation and thickness of the line so it doesn't get cropped at the corners
		margin = point_pos((0,0), thickness/2.0, -90, rotation)
		self.margin = map(abs, margin)
		w = abs(self.p1[0] - self.p2[0]) + self.margin[1] * 2
		h = abs(self.p1[1] - self.p2[1]) + self.margin[0] * 2
		super(Line, self).__init__(w, h, [thickness, color, STROKE_INNER], fill=None)
		if P.development_mode:
			f_vars = [length, rotation, self.p1[0], self.p1[1], self.p2[0], self.p2[1], self.surface_width, self.surface_height]
			print "Len {0}px at {1}deg: ({2}, {3}) => ({4}, {5}) on canvas ({6} x {7})".format(*f_vars)

		if auto_draw:
			self.draw()

	def __translate_to_positive__(self):
		# Translates line coordinates into aggdraw surface space (i.e. top-left corner becomes (0,0)) by offsetting the coordinates
		# such that the furthest left point is aligned to x=0 and the furthest up point is aligned to y=0.
		x_offset = -min(self.p1[0], self.p2[0])
		y_offset = -min(self.p1[1], self.p2[1])
		self.p1 = (self.p1[0] + x_offset, self.p1[1] + y_offset)
		self.p2 = (self.p2[0] + x_offset, self.p2[1] + y_offset)

	def draw(self, as_numpy_surface=False):
		x1 = self.p1[0] + (self.margin[1] + 1)
		y1 = self.p1[1] + (self.margin[0] + 1)
		x2 = self.p2[0] + (self.margin[1] + 1)
		y2 = self.p2[1] + (self.margin[0] + 1)
		self.surface.line((x1, y2, x2, y1), self.stroke)

		return self.surface


class Triangle(Drawbject):
	"""Creates a Drawbject containing an isoceles or equilateral triangle.

	Args:
		base (int): The width of the base of the triangle in pixels.
		height (int): The height of the triangle in pixels.
		rotation (float|int, optional): The degrees by which to rotate the triangle when
			rendering. Defaults to 0 (no rotation).
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the
			triangle, indicating the alignment (inner, center, or outer), width, and
			color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the triangle in RGB or RGBA format.
			Defaults to transparent fill.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified triangle.

	"""
	def __init__(self, base, height, rotation=0, stroke=None, fill=None):
		self.base = base
		self.height = height
		self.rotation = rotation

		super(Triangle, self).__init__(base, height, stroke, fill, rotation)

	def draw(self, as_numpy_surface=False):
		self.surface.polygon((1, 1, self.base // 2 + 1, self.height + 1, self.base + 1, 1), self.stroke, self.fill)

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
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the
			arrow, indicating the alignment (inner, center, or outer), width, and
			color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the arrow in RGB or RGBA format.
			Defaults to transparent fill.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified arrow.

	"""
	def __init__(self, tail_w, tail_h, head_w, head_h, rotation=0, stroke=None, fill=None):
		self.tail_w = tail_w
		self.tail_h = tail_h
		self.head_h = head_h
		self.head_w = head_w
		surf_x = self.head_w + self.tail_w
		surf_y = self.head_h if head_h > tail_h else tail_h
		super(Arrow, self).__init__(surf_x, surf_y, stroke, fill, rotation)


	def draw(self, as_numpy_surface=False):
		surf_cy = self.head_h // 2 if self.head_h > self.tail_h else self.tail_h // 2
		pts = []
		# start the tail
		pts += [1, (surf_cy - self.tail_h // 2) + 1]
		pts += [self.tail_w + 1, (surf_cy - self.tail_h // 2) + 1]
		# # draw the head
		pts += [self.tail_w + 1, (surf_cy - self.head_h // 2) + 1]
		pts += [self.tail_w + self.head_w + 1, surf_cy + 1]
		pts += [self.tail_w + 1, (surf_cy + self.head_h // 2) + 1]
		# finish the tail
		pts += [self.tail_w + 1, (surf_cy + self.tail_h // 2) + 1]
		pts += [1, (surf_cy +  self.tail_h // 2) + 1]
		self.surface.polygon(pts, self.stroke, self.fill)

		@property
		def __name__(self):
			return "Arrow"

class ColorWheel(Drawbject):
	"""Creates a Drawbject containing a color wheel. By default, the color wheel
	is constant-luminance.

	Manually specifying a color list for the color wheel is not yet supported, but
	is planned for a future release (e.g. specify an RGB wheel in place of a LAB one).

	Args:
		diameter (int): The diameter of the color wheel in pixels.
		thickness (int, optional): The width of the ring of the color wheel in pixels.
			Defaults to one quarter of the diameter if not specified.
		rotation (int, optional): The degrees by which to rotate the color wheel when
			rendered. Defaults to 0 (no rotation).
		auto_draw (bool): If True, internally draws the color wheel on initialization.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified color wheel.
		
	"""

	def __init__(self, diameter, thickness=None, rotation=0, auto_draw=True):
		# self.stroke_pad = int(diameter * 0.01)
		super(ColorWheel, self).__init__(diameter, diameter, stroke=None, fill=None)
		self.palette = colors
		self.rotation = rotation
		self.diameter = diameter
		self.radius = self.diameter // 2
		self.thickness = 0.25 * diameter if not thickness else thickness

		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=True):
		rotation = self.rotation
		for i in range(0, 360):
			brush = Brush(colors[i])
			center = self.surface_width // 2
			r = self.radius - 2
			vertices = [center, center]
			for i in range(0, 4):
				r_shift = -0.25 if i < 2 else 1.25
				r_shift += rotation
				func = cos if i % 2 else sin
				vertices.append(int(round(r + func(radians(r_shift) + radians(90)) * r)))
			self.surface.polygon(vertices, brush)
			rotation += 1

		inner_xy1 = self.thickness // 2
		inner_xy2 = self.surface_width - self.thickness // 2
		self.surface.ellipse((inner_xy1, inner_xy1, inner_xy2, inner_xy2), Brush((0,0,0,255)))
		return self

	def color_from_angle(self, angle, rotation=None):
		# allows function access with arbitrary rotation, such as is needed by ColorSelectionResponseCollector
		if not rotation:
			rotation = self.rotation
		# return self.palette[int(angle - rotation + 360 if angle < rotation else angle - rotation)]
		adj_angle = int(angle - rotation + 360 if angle < rotation else angle - rotation)
		print "Adjusted vals: {0}".format([angle, rotation, adj_angle])
		thick = adj_angle // 60 % 2 and 1 - (adj_angle % 60) / 60 or (adj_angle % 60) / 60
		colors = [[60, 1, thick, 0], # [...to_angle, red, green, blue],
				  [120, thick, 1, 0],
				  [180, 0, 1, thick],
				  [240, 0, thick, 1],
				  [360, thick, 0, 1],
				  [float('inf'), 1, 0, thick]]
		return tuple(int(c * 255) for c in colors[bisect([x[0] for x in colors], adj_angle)][1:])

	def angle_from_color(self, color, rotation=None):
		return self.palette.index(rgb_to_rgba(color))
		# allows function access with arbitrary rotation, such as is needed by ColorSelectionResponseCollector
		if not rotation: rotation = self.rotation
		color = [i / 255.0 for i in color]

		if color[0] == 1:
			if color[2] == 0:
				angle = color[1] * 60
			else:
				angle = 300 + (1 - color[2]) * 60
		elif color[1] == 1:
			if color[2] == 0:
				angle = 60 + (1 - color[0]) * 60
			else:
				angle = 120 + color[2] * 60
		else:
			if color[0] == 0:
				angle = 180 + (1 - color[1]) * 60
			else:
				angle = 240 + color[0] * 60
		angle -= rotation
		return 360 + angle if angle < 0 else angle
		# return angle + 360 if angle < rotation else angle

	@property
	def __name__(self):
		return "ColorWheel"



class FreeDraw(Drawbject):

	def __init__(self, width, height, stroke, origin=None, fill=None, auto_draw=True):
		super(FreeDraw, self).__init__(width, height, stroke, fill)
		self.origin = origin if origin else (0,0)
		self.at = self.origin
		self.closed = False
		self.sequence = []
		self.close_at = None

	def line(self, destination, origin=None):
		# if origin and origin != self.at:
		# 	self.move(origin)
		# else:
		# 	self.move(self.at)
		self.sequence.append([KLD_LINE, (destination[0], destination[1])])
		# self.at = destination

		return self

	def arc(self, destination, control, origin=None):
		# origin = self.__validate_ends(destination, origin)
		# x_ctrl = (destination[0] + control[0] // 2, control[1])
		# y_ctrl = (control[0], destination[1] + control[1] // 2)
		# self.__validate_ends([], x_ctrl)
		# self.__validate_ends([], y_ctrl)
		# if origin and origin != self.at:
		# 	self.move(origin)
		# else:
		# 	self.move(self.at)
		# arc_el =
		self.sequence.append([KLD_ARC, (list(origin) + list(control) + list(destination))])
		# self.move(destination)
		# self.at = destination

		return self

	def path(self, sequence, origin=None):
		self.sequence.append([KLD_PATH, sequence])
		self.at = sequence[-1]

		return self

	def move(self, location):
		self.sequence.append([KLD_MOVE, location])

	def draw_points(self, sequence):
		def chunks(s, n):
			for i in range(0, len(s), n):
				yield s[i:i + n]
		e_size = 3
		for s in chunks(sequence, 2):
			x1 = s[0] - e_size
			x2 = s[0] + e_size
			y1 = s[1] - e_size
			y2 = s[1] + e_size
			b = Brush((0,0,0))
			self.surface.ellipse([x1,y1,x2,y2], b)
			print "CHUNK! {0}".format([x1,y1,x2,y2])

	def draw(self, with_points=False):
		self.surface.rectangle([0,0,self.object_width, self.object_height], Brush((245, 245, 245)))

		# path_str = "M{0},{1}".format(*self.origin)
		path_str = ""
		for s in self.sequence:
			# if self.sequence[0] == s:
			# 	path_str += "M{0},{1}".format(s[1][0], s[1][1])
			if s[0] == KLD_MOVE:
				path_str += " M{0},{1}".format(s[1][0], s[1][1])
			if s[0]  == KLD_LINE:
				path_str += " L{0},{1}".format(*s[1])
			if s[0]  == KLD_ARC:
				path_str += " S{0},{1},{2},{3},{4},{5}".format(*s[1])
			if s[0]  == KLD_PATH:
				for p in s[1]:
					path_str += "L{0},{1}".format(*p)
		if self.close_at:
			path_str += " {0},{1}z".format(*self.close_at)
		p = Symbol(path_str)
		self.surface.symbol((0,0), p, self.stroke)

		return self

	def __validate_ends(self, sequence, origin):
		if not origin:
			if not self.at:
				return ValueError("Parameter 'at' not currently set and no origin provided.")
			origin = self.at
		try:
			if type(sequence[0]) is int:
				sequence = [sequence]
		except IndexError:
			pass
		# for loc in sequence:
		# 	if loc[0] not in range(0, self.object_width) or loc[1] not in range(0, self.object_height):
		# 		raise ValueError("Location ({0}, {1}) does not fall within surface bounds.".format(*loc))
		return origin

	@property
	def __name__(self):
		return "FreeDraw"

class Bezier(Drawbject):
	path_str = "m{0},{1} c{2},{3} {4},{5} {6},{7} z"
	path_str_2 = "m{0},{1} c{2},{3} {4},{5} {6},{7} s{8},{9} {10},{11} z"

	def __init__(self, height, width, origin, destination, ctrl1_s, ctrl1_e, ctrl2_s=None, ctrl2_e=None, stroke=None, fill=None, auto_draw=True):
		super(Bezier, self).__init__(width, height, stroke, fill)
		self.origin = origin
		self.destination = destination
		self.ctrl_start = ctrl1_s
		self.ctrl_end = ctrl1_e
		self.ctrl_2_start = ctrl2_s
		self.ctrl_2_end = ctrl2_e

		if auto_draw:
			self.draw()

	def draw(self):
		data = self.origin + self.ctrl_start + self.ctrl_end + self.destination
		path_str = self.path_str
		if self.ctrl_2_start and self.ctrl_2_end:
			data += self.ctrl_2_start
			data += self.ctrl_2_end
			path_str = self.path_str_2
		sym = Symbol(path_str.format(*data))
		self.surface.path((0,0), sym, self.stroke, self.fill)
		print self.fill_color
		print self.fill
		return self


	# # The following functions [bezier_curve() and pascal_row()]were written by the StackOverflow user @unutbu (#notypo)
	# # http://stackoverflow.com/questions/246525/how-can-i-draw-a-bezier-curve-using-pythons-pil
	# def __bezier_curve(self, xys):
	# 	# xys should be a sequence of 2-tuples (Bezier control points)
	# 	n = len(xys)
	# 	combinations = self.__pascal_row(n-1)
	# 	def bezier(ts):
	# 		# This uses the generalized formula for bezier curves
	# 		# http://en.wikipedia.org/wiki/B%C3%A9zier_curve#Generalization
	# 		result = []
	# 		for t in ts:
	# 			t_powers = (t**i for i in range(n))
	# 			u_powers = reversed([(1-t)**i for i in range(n)])
	# 			coeffficients = [c*a*b for c, a, b in zip(combinations, t_powers, u_powers)]
	# 			result.append(
	# 				tuple(sum([c*p for c, p in zip(coeffficients, ps)]) for ps in zip(*xys)))
	# 		return result
	# 	return bezier
	#
	# def __pascal_row(self, n):
	# 	# This returns the nth row of Pascal's Triangle
	# 	result = [1]
	# 	x, numerator = 1, n
	# 	for denominator in range(1, n//2+1):
	# 		# print(numerator,denominator,x)
	# 		x *= numerator
	# 		x /= denominator
	# 		result.append(x)
	# 		numerator -= 1
	# 	if n&1 == 0:
	# 		# n is even
	# 		result.extend(reversed(result[:-1]))
	# 	else:
	# 		result.extend(reversed(result))
	# 	return result

# class SVG(Drawbject):
#
# 	def __init__(self, filename, auto_draw=True):
# 		svg_start = re.compile("<path.*d=(.*)")
# 		svg_end = re.compile("(.*)/>\n")
# 		fpath = os.path.join(P.image_dir, filename+".svg")
# 		paths = []
# 		img = open(fpath).readlines()
# 		started = False
# 		for l in open(self.edf_path).readlines():
# 			if P_ID.match(l) is not None:
# 				id = P_ID.match(l).group(1)
# 			if START.match(l) is not None:
# 				t = Trial(START_TIME.match(l).group(1))
# 				continue
# 			if END.match(l) is not None:
# 				t.end = END_TIME.match(l).group(1)
# 				self.add_trial(t)
# 				t = None
# 				continue
# 			if t:
# 				t.add_line(l)
# 		for l in img:
# 			if svg_start.match()
#


#  to handle legacy code in which KLIBs had a Circle object rather than an Ellipse object
def Circle(diameter, stroke=None, fill=None, auto_draw=True):
	return Ellipse(diameter, diameter, stroke, fill, auto_draw)
