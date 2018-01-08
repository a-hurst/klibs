__author__ = 'jono'

import abc
from imp import load_source
from bisect import bisect
from os.path import join
from math import cos, sin, tan, atan, radians, ceil, sqrt

from aggdraw import Brush, Draw, Pen, Symbol
from PIL import Image
from numpy import asarray

from klibs.KLConstants import (STROKE_CENTER, STROKE_INNER, STROKE_OUTER,
	KLD_LINE, KLD_MOVE, KLD_ARC, KLD_PATH)
from klibs import P
from klibs.KLUtilities import point_pos, rotate_points, translate_points, canvas_size_from_points
from klibs.KLGraphics import rgb_to_rgba
from klibs.KLGraphics.colorspaces import const_lum

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

	transparent_brush = Brush((255, 0, 0), 0)

	def __init__(self, width, height, stroke, fill, rotation=0):
		super(Drawbject, self).__init__()

		self.surface = None
		self.canvas = None
		self.rendered = None

		self.__stroke = None
		self.stroke_width = 0
		self.stroke_color = None
		self.stroke_alignment = STROKE_INNER
		self.stroke = stroke

		self.__fill = None
		self.fill_color = None
		self.fill = fill

		self.__dimensions = None
		self.object_width = width
		self.object_height = height
		self.rotation = rotation

		self.init_surface()


	def __str__(self):
		return "klibs.Drawbject.{0} ({1} x {2}) at {3}".format(self.__name__, self.surface_width, self.surface_height, hex(id(self)))

	def init_surface(self):
		self._update_dimensions()
		self.rendered = None # Clear any existing rendered texture
		self.canvas = Image.new("RGBA", self.dimensions, (0, 0, 0, 0))
		self.surface = Draw(self.canvas)
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
		self.init_surface()
		self.draw()
		self.rendered = asarray(self.canvas)
		return self.rendered

	def _update_dimensions(self):
		pts = self._draw_points(outline=True)
		if pts != None:
			self.__dimensions = canvas_size_from_points(pts, flat=True)
		else:
			if self.stroke_alignment == STROKE_OUTER:
				stroke_w = self.stroke_width * 2
			elif self.stroke_alignment == STROKE_CENTER:
				stroke_w = self.stroke_width
			else:
				stroke_w = 0
			w, h = [self.object_width, self.object_height]
			self.__dimensions = [int(ceil(w+stroke_w))+2, int(ceil(h+stroke_w))+2]

	@property
	def dimensions(self):
		"""List[int, int]: The height and width of the internal surface on which the shape
		is drawn.
		"""
		return self.__dimensions

	@property
	def surface_width(self):
		return self.__dimensions[0]

	@property
	def surface_height(self):
		return self.__dimensions[1]

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
			self.stroke_width = 0
			self.stroke_color = None
			self.stroke_alignment = STROKE_INNER
			return self
		try:
			width, color, alignment = style
		except ValueError:
			width, color = style
			alignment = STROKE_INNER

		if alignment in [STROKE_INNER, STROKE_CENTER, STROKE_OUTER]:
			self.stroke_alignment = alignment
		else:
			raise ValueError("Invalid value provided for stroke alignment; see KLConstants for accepted values")

		color = list(color)
		if len(color)==3:
			color += [255]
		self.stroke_color = color
		self.stroke_width = width
		self.__stroke = Pen(tuple(color[:3]), width, color[3])
		if self.surface: # don't call this when initializing the Drawbject for the first time
			self.init_surface()
		return self

	@property
	def stroke_offset(self):
		if self.stroke_alignment == STROKE_OUTER:
			return self.stroke_width * 0.5
		if self.stroke_alignment == STROKE_INNER:
			return self.stroke_width * -0.5
		else:
			return 0 

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
		color = list(color)
		if len(color)==3:
			color += [255]
		self.fill_color = color
		self.__fill = Brush(tuple(color[:3]), color[3])
		if self.surface: # don't call this when initializing the Drawbject for the first time
			self.init_surface()
		return self

	@abc.abstractmethod
	def _draw_points(self, outline=False):
		return None

	@abc.abstractmethod
	def draw(self):
		pts = self._draw_points()
		dx = self.surface_width / 2.0
		dy = self.surface_height / 2.0
		pts = translate_points(pts, delta=(dx, dy), flat=True)
		
		self.surface.polygon(pts, self.stroke, self.fill)
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
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the cross,
			indicating the alignment of the stroke (inner, center, or outer), the stroke
			width, and the color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the cross in RGB or RGBA format.
			Defaults to transparent fill.
		rotation (numeric, optional): The angle in degrees by which to rotate the cross 
			when rendered. Defaults to 0 (no rotation).
		auto_draw (bool, optional): If True, draws the shape internally when created.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified fixation cross.

	"""
	def __init__(self, size, thickness, stroke=None, fill=None, rotation=0, auto_draw=True):
		self.thickness = thickness
		super(FixationCross, self).__init__(size, size, stroke, fill, rotation)
		if stroke == None:
			self._Drawbject__stroke = Pen((0, 0, 0), 0, 0)
		if auto_draw:
			self.draw()

	def _draw_points(self, outline=False):
		sw = self.stroke_width
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
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the ellipse,
			indicating the alignment (inner, center, or outer), width, and color of the
			stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the ellipse in RGB or RGBA
			format. Defaults to transparent fill.
		auto_draw (bool, optional): If True, internally draws the ellipse on initialization.	

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified ellipse.

	"""

	def __init__(self, width, height=None, stroke=None, fill=None, auto_draw=True):
		if not height:
			height = width
		super(Ellipse, self).__init__(width, height, stroke, fill)
		if auto_draw:
			self.draw()

	def draw(self):
		surf_c = self.surface_width / 2.0 # center of the drawing surface
		x1 = surf_c-(self.object_width/2.0 + self.stroke_offset)
		y1 = surf_c-(self.object_height/2.0 + self.stroke_offset)
		x2 = surf_c+(self.object_width/2.0 + self.stroke_offset)
		y2 = surf_c+(self.object_height/2.0 + self.stroke_offset)
		self.surface.ellipse([x1, y1, x2, y2], self.stroke, self.fill)
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
		thickness (int): The thickness of the ring of the annulus in pixels.
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the
			annulus, indicating the alignment (inner, center, or outer), width, and
			color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the annulus in RGB or RGBA
			format. Defaults to transparent fill.
		auto_draw (bool): If True, internally draws the annulus on initialization.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified annulus.

	"""

	def __init__(self, diameter, thickness, stroke=None, fill=None, auto_draw=True):
		self.thickness = thickness
		self.diameter = diameter
		self.radius = self.diameter / 2.0
		super(Annulus, self).__init__(diameter, diameter, stroke, fill)
		if not stroke:
			self.stroke_color = (0,0,0,0)
			self.stroke_width = 0

		if self.thickness > self.radius:
			raise ValueError("Thickness of annulus larger than radius; decrease thickness or increase diameter")
		if auto_draw:
			self.draw()

	def draw(self):
		surf_c = self.surface_width / 2.0 # center of the drawing surface
		if self.stroke:
			if self.stroke_alignment == STROKE_CENTER:
				stroke_pen = Pen(tuple(self.stroke_color), self.stroke_width/2.0)
				# draw outer stroke ring
				xy_1 = surf_c - (self.radius+self.stroke_width/4.0)
				xy_2 = surf_c + (self.radius+self.stroke_width/4.0)
				self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroke_pen, self.transparent_brush)
				# draw inner stroke ring
				xy_1 = surf_c - (self.radius-(self.thickness+self.stroke_width/4.0))
				xy_2 = surf_c + (self.radius-(self.thickness+self.stroke_width/4.0))
				self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroke_pen, self.transparent_brush)
			else:
				if self.stroke_alignment == STROKE_OUTER:
					xy_1 = surf_c - (self.radius+self.stroke_width/2.0)
					xy_2 = surf_c + (self.radius+self.stroke_width/2.0)
				elif self.stroke_alignment == STROKE_INNER:
					xy_1 = surf_c - (self.radius-(self.thickness+self.stroke_width/2.0))
					xy_2 = surf_c + (self.radius-(self.thickness+self.stroke_width/2.0))
				stroke_pen = Pen(tuple(self.stroke_color), self.stroke_width)
				self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroke_pen, self.transparent_brush)
		if self.fill:
			xy_1 = surf_c - (self.radius-self.thickness/2.0)
			xy_2 = surf_c + (self.radius-self.thickness/2.0)
			ring_pen = Pen(tuple(self.fill_color), self.thickness)
			self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], ring_pen, self.transparent_brush)
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
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the
			rectangle, indicating the alignment (inner, center, or outer), width, and
			color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the rectangle in RGB or RGBA
			format. Defaults to transparent fill.
		rotation (numeric, optional): The angle in degrees by which to rotate the rectangle
			when rendered. Defaults to 0 (no rotation).
		auto_draw (bool, optional): If True, draws the rectangle internally when created.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified rectangle.

	"""

	def __init__(self, width, height=None, stroke=None, fill=None, rotation=0, auto_draw=True):
		if not height:
			height = width
		super(Rectangle, self).__init__(width, height, stroke, fill, rotation)
		if auto_draw:
			self.draw()
	
	def _draw_points(self, outline=False):
		so = self.stroke_offset + self.stroke_width / 2.0 if outline else self.stroke_offset
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
	"""Creates a Drawbject containing a six-spoke asterisk.

	Args:
		size (int): The height and width of the asterisk in pixels.
		fill (Tuple[color]): The color of the asterisk, expressed as an iterable of
			integer values from 0 to 255 representing an RGB or RGBA color.
		thickness (int, optional): The thickness of the asterisk in pixels. Defaults to '1'
			if no value is given.
		rotation (numeric, optional): The angle in degrees by which to rotate the asterisk 
			when rendered. Defaults to 0 (no rotation).
		auto_draw (bool, optional): If True, draws the shape internally when created.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified asterisk.

	"""
	def __init__(self, size, fill, thickness=1, rotation=0, auto_draw=True):
		self.size = size
		self.thickness = thickness
		super(Asterisk, self).__init__(size, size, None, fill, rotation)
		self._Drawbject__stroke = Pen((0, 0, 0), 0, 0)
		if auto_draw:
			self.draw()

	def _draw_points(self, outline=False):
		ht = self.thickness / 2.0 # half of the asterisk's thickness
		hs = self.size / 2.0 # half of the asterisk's size
		spokes = 6
		pts = []
		for s in range(0, spokes):
			spoke = [-ht, ht, -ht, hs, ht, hs, ht, ht]
			pts += rotate_points(spoke, (0, 0), s*(-360.0/spokes), flat=True)
		if self.rotation != 0:
			pts = rotate_points(pts, (0, 0), self.rotation, flat=True)
		return pts

	@property
	def __name__(self):
		return "Asterisk"


class Asterisk2(Drawbject):
	"""Creates a Drawbject containing an eight-spoke asterisk with somewhat square dimensions.

	Args:
		size (int): The height and width of the asterisk in pixels.
		fill (Tuple[color]): The color of the asterisk, expressed as an iterable of
			integer values from 0 to 255 representing an RGB or RGBA color.
		thickness (int, optional): The thickness of the asterisk in pixels. Defaults to '1'
			if no value is given.
		rotation (numeric, optional): The angle in degrees by which to rotate the asterisk 
			when rendered. Defaults to 0 (no rotation).
		auto_draw (bool, optional): If True, draws the shape internally when created.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified asterisk.

	"""
	def __init__(self, size, fill, thickness=1, rotation=0, auto_draw=True):
		self.size = size
		self.thickness = thickness
		super(Asterisk2, self).__init__(size, size, None, fill, rotation)
		self._Drawbject__stroke = Pen((0, 0, 0), 0, 0)
		if auto_draw:
			self.draw()
	
	def _draw_points(self, outline=False):
		ht = self.thickness / 2.0 # half of the asterisk's thickness
		hss = self.size / 2.0 # half of the asterisk's straight (vertical/horizontal) size
		hds = sqrt(2*(hss**2)) # half of the asterisk's diagonail size
		spokes = 8
		pts = []
		for s in range(0, spokes):
			hs = hss if s%2 == 0 else hds
			spoke = [-ht, ht, -ht, hs, ht, hs, ht, ht]
			pts += rotate_points(spoke, (0, 0), s*(-360.0/spokes), flat=True)
		if self.rotation != 0:
			pts = rotate_points(pts, (0, 0), self.rotation, flat=True)
		return pts

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

	def draw(self):
		x1 = self.p1[0] + (self.margin[1] + 1)
		y1 = self.p1[1] + (self.margin[0] + 1)
		x2 = self.p2[0] + (self.margin[1] + 1)
		y2 = self.p2[1] + (self.margin[0] + 1)
		self.surface.line((x1, y2, x2, y1), self.stroke)
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
		stroke (List[alignment, width, Tuple[color]], optional): The stroke of the
			triangle, indicating the alignment (inner, center, or outer), width, and
			color of the stroke. Defaults to no stroke.
		fill (Tuple[color], optional): The fill color for the triangle in RGB or RGBA format.
			Defaults to transparent fill.
		rotation (numeric, optional): The angle in degrees by which to rotate the triangle
			when rendered. Defaults to 0 (no rotation).

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified triangle.

	"""
	def __init__(self, base, height=None, stroke=None, fill=None, rotation=0):
		self.base = base
		if not height: # if no height given, draw equilateral
			height = base/2.0 * sqrt(3)
		self.height = height
		super(Triangle, self).__init__(base, height, stroke, fill, rotation)
	
	def _draw_points(self, outline=False):
		so = self.stroke_offset + self.stroke_width / 2.0 if outline else self.stroke_offset
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
		arrow_w = self.head_w + self.tail_w
		arrow_h = self.head_h if head_h > tail_h else tail_h
		super(Arrow, self).__init__(arrow_w, arrow_h, stroke, fill, rotation)
		# Set stroke to empty pen to avoid aggdraw anti-aliasing weirdness
		if stroke == None:
			self._Drawbject__stroke = Pen((0, 0, 0), 0, 0)
	
	def _draw_points(self, outline=False):
		so = self.stroke_offset + self.stroke_width / 2.0 if outline else self.stroke_offset
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
		colorspace (:obj:`list`, optional): The list of colours to render the colour
			wheel with, in the form of RGB or RGBA tuples. Defaults to a CIELUV
			constant-luminance colour wheel if not specified.
		rotation (int, optional): The angle in degrees by which to rotate the color wheel
			when rendered. Defaults to 0 (no rotation).
		auto_draw (bool): If True, internally draws the color wheel on initialization.

	Returns:
		:obj:`KLDraw.Drawbject`: A Drawbject containing the specified color wheel.
		
	"""

	def __init__(self, diameter, thickness=None, colorspace=None, rotation=0, auto_draw=True):
		if colorspace == None:
			colorspace = const_lum
		self.palette = colorspace
		self.diameter = diameter
		self.radius = self.diameter / 2.0
		self.thickness = 0.20 * diameter if not thickness else thickness
		super(ColorWheel, self).__init__(diameter, diameter, None, None, rotation)
		if auto_draw:
			self.draw()

	def draw(self):
		rotation = self.rotation
		center = self.surface_width / 2.0
		r = self.radius + 1
		for i in range(0, len(self.palette)):
			brush = Brush(rgb_to_rgba(self.palette[i]))
			vertices = [center, center]
			for i in range(0, 4):
				r_shift = -0.25 if i < 2 else 1.25
				r_shift -= rotation
				func = cos if i % 2 else sin
				vertices.append(r + r * func(radians(r_shift+180)))
			self.surface.polygon(vertices, brush)
			rotation += 360.0 / len(self.palette)
		self.surface.flush()

		# Create annulus mask and apply it to colour disc
		mask = Image.new('L', (self.surface_width, self.surface_height), 0)
		d = Draw(mask)
		xy_1 = center - (self.radius-self.thickness/2.0)
		xy_2 = center + (self.radius-self.thickness/2.0)
		path_pen = Pen(255, self.thickness)
		d.ellipse([xy_1, xy_1, xy_2, xy_2], path_pen, self.transparent_brush)
		d.flush()
		self.canvas.putalpha(mask)

		return self.canvas

	def color_from_angle(self, angle, rotation=None):
		# allows function access with arbitrary rotation, such as is needed by ColorSelectionResponseCollector
		if not rotation:
			rotation = self.rotation
		
		degrees_per_colour = 360.0/len(self.palette)
		adj_angle = (angle - rotation) % 360
		i = int(adj_angle/degrees_per_colour)
		color = self.palette[i]
		return color

	def angle_from_color(self, color, rotation=None):
		# allows function access with arbitrary rotation, such as is needed by ColorSelectionResponseCollector
		#TODO: return true middle when two or more adjacent colours are the same
		if not rotation:
			rotation = self.rotation

		try:
			i = self.palette.index(rgb_to_rgba(color))
		except ValueError:
			raise ValueError("The color {0} does not exist in the color wheel palette.".format(rgb_to_rgba(color)))
		degrees_per_colour = 360.0/len(self.palette)
		angle = ((i+0.5) * degrees_per_colour + rotation) % 360
		return angle

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
		self.surface.flush()

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
		self.surface.flush()
		return self.canvas

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
		self.surface.flush()
		return self.canvas


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

# polygon
	#hs = self.size / 2.0 # half of the asterisk's size
	#sides = 6
	#pts = []
	#for s in range(0, sides):
	#	pts += rotate_points([0, hs], (0, 0), s*(360.0/sides), flat=True)
