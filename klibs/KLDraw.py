__author__ = 'jono'

from PIL import Image
import aggdraw
import numpy
from KLConstants import *
from KLNumpySurface import *
from KLUtilities import *
import abc


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

	return NumpySurface(draw_context)

class Drawbject(object):
	__stroke = None
	__fill = None
	stroke_offset = 0
	width = None
	height = None

	def __init__(self, surface_x, surface_y, stroke, fill):
		super(Drawbject, self).__init__()
		try:
			test = iter(stroke)
			self.stroke = stroke
			surface_x += stroke[0]
			surface_y += stroke[0]
			self.stroke_offset = stroke[0] // 2
		except TypeError:
			pass
		try:
			self.fill = fill
		except TypeError:
			pass
		self.width = surface_x
		self.height = surface_y
		self.surface = aggdraw.Draw("RGBA", [surface_x, surface_y], (0, 0, 0, 0))

	def render(self):
		surface_bytes = Image.frombytes(self.surface.mode, self.surface.size, self.surface.tostring())
		return NumpySurface(numpy.asarray(surface_bytes))

	@property
	def stroke(self):
		return self.__stroke

	@stroke.setter
	def stroke(self, style):
		width, color = style
		if len(color) == 4:
			opacity = color[3]
			color = [i for i in color[0:3]]
		else:
			color = [i for i in color]
			opacity = 255
		self.__stroke = aggdraw.Pen(tuple(color), width, opacity)

	@property
	def fill(self):
		return self.__fill

	@fill.setter
	def fill(self, color):
		if len(color) == 4:
			opacity = color[3]
			color = tuple(color[0:3])
		else:
			color = tuple(color)
			opacity = 255
		self.__fill = aggdraw.Brush(color, opacity)

	@abc.abstractmethod
	def draw(self):
		pass



class FixationCross(Drawbject):

	def __init__(self, width, stroke, color=None, fill=None):
		Drawbject.__init__(self, width, width)
		if fill is None:
			fill = Params.default_fill_color
		if color is None:
			color = (abs(255 - fill[0]), abs(255 - fill[1]), abs(255 - fill[2]), 255)  # invert default fill if no color
		cross_pen = aggdraw.Pen(color, stroke, 255)
		self.surface = aggdraw.Draw("RGBA", (width, width), fill)
		self.surface.line((width // 2, 0, width // 2, width), cross_pen)
		self.surface.line((0, width // 2, width, width // 2), cross_pen)


class Circle(Drawbject):
	diameter = None

	def __init__(self, diameter, stroke=None, fill=None, auto_draw=True):
		super(Circle, self).__init__(diameter + 2, diameter + 2, stroke, fill)
		self.diameter = diameter
		if auto_draw:
			self.draw()


	def draw(self):
		xy_1 = self.stroke_offset + 1
		xy_2 = self.diameter
		self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], self.stroke, self.fill)
		return self
