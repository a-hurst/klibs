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
	transparent_brush = Brush((255, 0, 0), 0)

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
		self.rendered = None

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
		self.init_surface()
		self.draw()
		surface_bytes = frombytes(self.surface.mode, self.surface.size, self.surface.tostring())
		self.rendered = NpS(asarray(surface_bytes)).render()
		return self.rendered

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
		self.__stroke = Pen(tuple(color), width, opacity)
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
			opacity = color[3] if type(color[3]) is int else int(color[3] * 255)
			color = tuple(color[0:3])
		else:
			color = tuple(color)
			opacity = 255
		self.fill_color = color
		self.__fill = Brush(color, opacity)
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
			self.stroke_color = (0,0,0,0)
			self.stroke_width = 0
		if auto_draw:
			self.draw()

	def draw(self,  as_numpy_surface=False):
		if self.stroke:
			stroked_path_pen = Pen(tuple(self.stroke_color), self.ring_width)
			xy_1 = 2 + self.ring_width
			xy_2 = self.surface_width - (2 + self.ring_width)
			self.surface.ellipse([xy_1, xy_1, xy_2, xy_2], stroked_path_pen, self.transparent_brush)
		xy_1 = 2 + self.ring_width
		xy_2 = self.surface_width - (2 + self.ring_width)
		path_pen = Pen(tuple(self.fill_color), self.ring_inner_width)
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

	def __init__(self, length, color, thickness, rotation=0, pts=None, auto_draw=True):
		self.rotation = rotation
		if pts:
			self.p1, self.p2 = pts
		else:
			self.p1 = (0,0)
			self.p2 = point_pos(self.p1, length, rotation)

		self.__translate_to_positive__()
		w = thickness + self.p2[0]
		h = thickness + self.p1[1] if self.p1[1] > self.p2[1] else self.p2[1]
		super(Line, self).__init__(w + thickness, h + thickness, [thickness, color, STROKE_INNER], fill=None)
		f_vars = [length, rotation, self.p1[0], self.p1[1], self.p2[0], self.p2[1], self.surface_width, self.surface_height]
		print "Len {0}px at {1}deg: ({2}, {3}) => ({4}, {5}) on canvas ({6} x {7})".format(*f_vars)
		# super(Line, self).__init__(self.p2[0] + thickness, self.p2[1] + thickness, [thickness, color, STROKE_INNER], fill=None)

		if auto_draw:
			self.draw()

	def __translate_to_positive__(self):
		self.p1 = (self.p1[0] - self.p1[0], abs(self.p1[1]))
		self.p2 = (self.p2[0] - self.p2[0], abs(self.p2[1]))

		# ie. x1_trans = 2 * mid_p[x] - x1, y1=y1; ghislain and jon worked this out
		x_trans = 2 *midpoint(self.p1, self.p2)[0]
		self.p1 = (x_trans - self.p1[0], self.p1[1])
		self.p2 = (x_trans - self.p2[0], self.p2[1])


	def draw(self, as_numpy_surface=False):
		self.surface.line((self.p1[0]+1, self.p1[1]+1, self.p2[0], self.p2[1]), self.stroke)

		return self.surface



class ColorWheel(Drawbject):

	def __init__(self, diameter, thickness=None,  rotation=0, auto_draw=True):
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
