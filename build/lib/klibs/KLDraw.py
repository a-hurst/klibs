__author__ = 'jono'

from PIL import Image
import aggdraw
import numpy
from KLConstants import *
from KLNumpySurface import *
from KLUtilities import *
import abc

def cursor():
		dc =  aggdraw.Draw("RGBA", [32, 32], (0, 0, 0, 0))
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

class Drawbject(object):
	surface = None

	def __init__(self):
		pass

	@abc.abstractmethod
	def draw(self):
		return


class FixationCross(Drawbject):
	surface = None

	def __init__(self, width, stroke, color=None, fill=None):
		Drawbject.__init__(self)
		if fill is None:
			fill = Params.default_fill_color
		if color is None:
			color = (abs(255 - fill[0]), abs(255 - fill[1]), abs(255 - fill[2]), 255)  # invert default fill if no color
		cross_pen = aggdraw.Pen(color, stroke, 255)
		self.surface = aggdraw.Draw("RGBA", (width, width), fill)
		self.surface.line((width // 2, 0, width // 2, width), cross_pen)
		self.surface.line((0, width // 2, width, width // 2), cross_pen)

	def draw(self):
		bytes = Image.frombytes(self.surface.mode, self.surface.size, self.surface.tostring())
		return NumpySurface(numpy.asarray(bytes))
