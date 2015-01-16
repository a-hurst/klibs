__author__ = 'jono'

from PIL import Image
import aggdraw
import numpy
from KLConstants import *
from KLNumpySurface import *
from KLUtilities import *
import abc


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
