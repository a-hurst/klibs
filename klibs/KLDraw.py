__author__ = 'jono'

import abc

import aggdraw
from klibs.KLNumpySurface import *
from klibs.KLUtilities import *
from klibs.KLTextManager import TextStyle
from math import pi as PI
from imp import load_source


######################################################################
#
# aggdraw Documentation: http://effbot.org/zone/pythondoc-aggdraw.htm
#
######################################################################


def cursor(color=None):
	dc =  aggdraw.Draw("RGBA", [32, 32], (0, 0, 0, 0))
	if color is not None:
		cursor_color = color[0:3]
	else:
		cursor_color = []
		for c in Params.default_fill_color:
			cursor_color.append(abs(c - 255))
		cursor_color = cursor_color[0:3]
	# coordinate tuples are easier to read/modify but aggdraw needs a stupid x,y,x,y,x,y list, so... :S
	cursor_coords = [(6, 0), (6, 27), (12, 21), (18, 32), (20, 30), (15, 20), (23, 20), (6, 0)]
	cursor_xy_list = []
	for point in cursor_coords:
		cursor_xy_list.append(point[0])
		cursor_xy_list.append(point[1])
	brush = aggdraw.Brush(tuple(cursor_color), 255)
	pen = aggdraw.Pen((255,255,255), 1, 255)
	dc.polygon(cursor_xy_list, pen, brush)
	cursor_surface = from_aggdraw_context(dc)
	return cursor_surface


def drift_correct_target():
	draw_context_length = Params.screen_y // 60
	while draw_context_length % 3 != 0:  # center-dot is 1/3 of parent; offset unequal if parent not divisible by 3
		draw_context_length += 1
	black_brush = aggdraw.Brush((0, 0, 0, 255))
	white_brush = aggdraw.Brush((255, 255, 255, 255))
	draw_context = aggdraw.Draw("RGBA", [draw_context_length + 2, draw_context_length + 2], (0, 0, 0, 0))
	draw_context.ellipse([0, 0, draw_context_length, draw_context_length], black_brush)
	wd_top = draw_context_length // 3  #ie. white_dot_top, the inner white dot of the calibration point
	wd_bot = 2 * draw_context_length // 3
	draw_context.ellipse([wd_top, wd_top, wd_bot, wd_bot], white_brush)

	return from_aggdraw_context(draw_context)

colors = load_source("*", os.path.join(Params.klibs_dir, "color_wheel_color_list.py")).colors

class Drawbject(object):
	transparent_brush = aggdraw.Brush((255, 0, 0), 0)

	def __init__(self, width, height, stroke, fill):
		super(Drawbject, self).__init__()

		self.__stroke = None
		self.stroke_color = None
		self.stroke_width = None
		self.stroke_alignment = STROKE_INNER
		self.__fill = None
		self.fill_color = None
		self.stroke_width = 0
		self.object_width = width
		self.object_height = height
		self.surface_width = None
		self.surface_height = None
		self.surface = None

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
		self.surface = aggdraw.Draw("RGBA", [self.surface_width, self.surface_height], (0, 0, 0, 0))
		self.surface.setantialias(True)

	def render(self):
		self.init_surface()
		self.draw()
		surface_bytes = Image.frombytes(self.surface.mode, self.surface.size, self.surface.tostring())
		return NumpySurface(numpy.asarray(surface_bytes))

	@abc.abstractproperty
	def __name__(self):
		pass

	@property
	def stroke(self):
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
			opacity = color[3]
			color = [i for i in color[0:3]]
		else:
			color = [i for i in color]
			opacity = 255
		self.stroke_color = color
		self.stroke_width = width
		self.__stroke = aggdraw.Pen(tuple(color), width, opacity)
		if self.surface: # don't call this when initializing the Drawbject for the first time
			self.init_surface()
		return self

	@property
	def fill(self):
		return self.__fill

	@fill.setter
	def fill(self, color):
		if not color:
			self.fill_color = None
			return self
		if len(color) == 4:
			opacity = color[3]
			color = tuple(color[0:3])
		else:
			color = tuple(color)
			opacity = 255
		self.fill_color = color
		self.__fill = aggdraw.Brush(color, opacity)
		if self.surface: # don't call this when initializing the Drawbject for the first time
			self.init_surface()
		return self

	@abc.abstractmethod
	def draw(self, as_numpy_surface=False):
		pass

	@property
	def dimensions(self):
		return [self.surface_width, self.surface_height]


class FixationCross(Drawbject):

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

	def __init__(self, width, height=None, stroke=None, fill=None, auto_draw=True):
		if not height:
			height = width
		super(Ellipse, self).__init__(width, height, stroke, fill)
		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=False):
		xy_1 = self.stroke_width + 1
		x_2 = self.surface_width - 1
		y_2 = self.surface_height - 1
		self.surface.ellipse([xy_1, xy_1, x_2, y_2], self.stroke, self.fill)
		return self

	@property
	def __name__(self):
		return "Ellipse"
	
	@property
	def width(self):
		return self.object_width
	
	@width.setter
	def width(self, value):
		self.object_width = value
		self.init_surface()

	@property
	def height(self):
		return self.object_height
	
	
	@height.setter
	def height(self, value):
		self.object_height = value
		self.init_surface()

	@property
	def diameter(self):
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

	def __init__(self, diameter, ring_width, stroke=None, fill=None, auto_draw=True):
		super(Annulus, self).__init__(diameter + 2, diameter + 2, stroke, fill)
		self.ring_width = ring_width
		try:
			self.ring_inner_width = ring_width - 2 * stroke[0]
		except TypeError:
			self.ring_inner_width = ring_width
		if self.ring_inner_width < 1:
			raise ValueError("Annulus area subsumed by stroke; increase ring_width or decrease stroke size")
		if stroke is None:
			self.stroke_color = (0,0,0)
			self.stroke_width = 0
		if auto_draw:
			self.draw()


	def draw(self,  as_numpy_surface=False):
		if self.stroke:
			stroked_path_pen = aggdraw.Pen(tuple(self.stroke_color), self.ring_width)
			xy_1 = 2 + self.ring_width
			xy_2 = self.surface_width - (2 + self.ring_width)
			self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroked_path_pen, self.transparent_brush)
		xy_1 = 2 + self.ring_width
		xy_2 = self.surface_width - (2 + self.ring_width)
		path_pen = aggdraw.Pen(tuple(self.fill_color), self.ring_inner_width)
		self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], path_pen, self.transparent_brush)

		return self

	@property
	def __name__(self):
		return "Annulus"


class Rectangle(Drawbject):

	def __init__(self, width, height=None, stroke=None, fill=None, auto_draw=True):
		if not height:
			height = width
		super(Rectangle, self).__init__(width, height, stroke, fill)
		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=False):
		x1 = self.stroke_width + 1
		y1 = self.stroke_width + 1
		x2 = self.surface_width - (self.stroke_width + 1)
		y2 = self.surface_height - (self.stroke_width + 1)
		if self.stroke:
			if self.fill:
				self.surface.rectangle((x1, y1, x2, y2), self.stroke, self.fill)
			else:
				self.surface.rectangle((x1, y1, x2, y2), self.stroke)
		else:
			self.surface.rectangle((1, 1, self.surface_width - 1, self.surface_height - 1), self.fill)

		return self

	@property
	def __name__(self):
		return "Rectangle"


class Asterisk(Drawbject):

	def __init__(self, size, color, stroke=1, auto_draw=True):
		stroke = int(0.2 * size)
		super(Asterisk, self).__init__(size, size, (stroke, color), fill=None)
		self.size = size
		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=False):
		x_os = int(self.surface_width * 0.925)
		y_os = int(self.surface_height * 0.75)
		l1 = [self.surface_width // 2 + 1, 1, self.surface_width // 2 + 1, self.surface_height - 1]
		l2 = [x_os + 1, y_os +1, self.surface_width - x_os + 1, self.surface_height - y_os + 1]
		l3 = [self.surface_width - (x_os + 1), y_os + 1, x_os + 1, self.surface_height - y_os + 1]
		self.surface.line([l1[0], l1[1], l1[2],l1[3]], self.stroke)
		self.surface.line([l2[0], l2[1], l2[2],l2[3]], self.stroke)
		self.surface.line([l3[0], l3[1], l3[2],l3[3]], self.stroke)

		return self

	@property
	def __name__(self):
		return "Asterisk"


class Line(Drawbject):

	def __init__(self, length, color, thickness, rotation=0, auto_draw=True):
		self.rotation = rotation
		if rotation % 90 != 0:
			self.x1 = thickness // 2
			self.y1 = thickness // 2
			self.x2 = int(math.sin(math.radians(float(self.rotation))) * length)
			self.y2 = int(math.cos(math.radians(float(self.rotation))) * length)
			s_width = self.x2 + int(0.5 * thickness)
			s_height = self.y2 + int(0.5 * thickness)
		else:
			if rotation in [0, 180]:
				s_width = thickness
				s_height = length
				self.x1 = thickness // 2
				self.y1 = 1
				self.x2 = self.x1
				self.y2 = length
			else:
				s_width = length
				s_height = thickness
				self.x1 = 1
				self.y1 = thickness // 2
				self.x2 = length
				self.y2 = self.x1
		super(Line, self).__init__(s_width, s_height, [thickness, color, STROKE_INNER], fill=None)

		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=False):
		self.surface.line((self.x1, self.y1, self.x2, self.y2), self.stroke)

		return self.surface

class ColorWheel(Drawbject):

	def __init__(self, diameter, thickness=None,  rotation=0, auto_draw=True):
		# self.stroke_pad = int(diameter * 0.01)
		super(ColorWheel, self).__init__(diameter, diameter, stroke=None, fill=None)
		self.rotation = rotation
		self.diameter = diameter
		self.radius = self.diameter // 2
		self.thickness = 0.25 * diameter if not thickness else thickness

		if auto_draw:
			self.draw()

	def draw(self, as_numpy_surface=True):
		for i in range(360):
			brush = aggdraw.Brush(colors[i])
			center = self.surface_width // 2
			inner_radius = self.radius - 2
			self.surface.polygon((center, center,
						   int(round(inner_radius + math.sin((self.rotation - .25) * PI / 180) * inner_radius)),
						   int(round(inner_radius + math.cos((self.rotation - .25) * PI / 180) * inner_radius)),
						   int(round(inner_radius + math.sin((self.rotation + 1.25) * PI / 180) * inner_radius)),
						   int(round(inner_radius + math.cos((self.rotation + 1.25) * PI / 180) * inner_radius))),
						  brush)
			self.rotation += 1
			if self.rotation > 360:
				self.rotation -= 360
		inner_xy1 = self.thickness // 2
		inner_xy2 = self.surface_width - self.thickness // 2
		outer_xy1 = 0
		outer_xy2 = self.surface_width
		self.surface.ellipse((inner_xy1, inner_xy1, inner_xy2, inner_xy2), aggdraw.Brush((0,0,0,255)))

		return self
		# self.surface.ellipse((0, 0, outer_xy2, outer_xy2), aggdraw.Pen((0, 0, 0, 255), self.stroke_pad))
		# print self.surface
		# return self.surface if not as_numpy_surface else NumpySurface(self.surface)

	@property
	def __name__(self):
		return "ColorWheel"


#  to handle legacy code in which KLIBs had a Circle object rather than an Ellipse object
def Circle(diameter, stroke=None, fill=None, auto_draw=True):
	return Ellipse(diameter, diameter, stroke, fill, auto_draw)
