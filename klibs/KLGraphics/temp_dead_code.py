# try:
# 	# python3
# 	class Point(namedtuple):
# 		x: int
# 		y: int = 1  # Set default value
#
#
# 	class RGBAColor(namedtuple):
# 		red: int = 0
# 		green: int = 0
# 		blue: int = 0
# 		alpha: int = 0
# except SyntaxError:

# def init_canvas(self):
	# 	if all(i is None for i in [self.background, self.foreground, self.width, self.height]):
	# 		self.foreground = np.zeros((1,1,4))
	# 		self.background = np.zeros((1,1,4))
	# 	else:
	# 		if self.foreground is None:
	# 			try:
	# 				fg_width = self.background.shape[1] if self.background.shape[1] > self.width else self.width
	# 			except AttributeError:
	# 				fg_width = self.width
	# 			try:
	# 				fg_height = self.background.shape[0] if self.background.shape[0] > self.height else self.height
	# 			except AttributeError:
	# 				fg_height = self.height
	# 			self.foreground = np.zeros((fg_height, fg_width, 4))
	#
	# 		if self.background is None:
	# 			try:
	# 				bg_width = self.foreground.shape[1] if self.foreground.shape[1] > self.width else self.width
	# 			except AttributeError:
	# 				bg_width = self.width
	# 			try:
	# 				bg_height = self.foreground.shape[0] if self.foreground.shape[0] > self.height else self.height
	# 			except AttributeError:
	# 				bg_height = self.height
	#
	# 			self.background = np.zeros((bg_height, bg_width, 4))
	# 	self._update_shape__()


# def average_color(self, layer=None):
	# 	# nope, doesn't work; were working it out with Ross but then you couldn't finish
	# 	try:
	# 		px = self.rendered if not layer else self.layers[layer]
	# 		iter(px)
	# 	except TypeError:
	# 		px = self.render()
	# 	px_count = px.shape[0] * px.shape[1]
	# 	new_px = px.reshape((px_count,4))
	# 	print(new_px.shape)


# def layer_from_file(self, image, layer=NS_FOREGROUND, location=None):
	# 	# todo: better error handling; check if the file has a valid image extension, make sure path is a valid type
	# 	"""
	#
	# 	:param image:
	# 	:param layer:
	# 	:param location:
	# 	:return: :raise TypeError:
	# 	"""
	# 	image_content = add_alpha_channel(np.array(Image.open(image)))
	#
	# 	if layer == NS_FOREGROUND:
	# 		self.foreground = image_content
	# 	elif layer == NS_BACKGROUND:
	# 		self._set_background__(image_content)
	# 	else:
	# 		TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")
	#
	# 	self._update_shape__()  # only needed if resize not called; __update_shape called at the end of resize
	# 	return self

	# def location_in_layer_bounds(self, location, layer=None):
	# 	"""
	#
	# 	:param location:
	# 	:param layer:
	# 	:return: :raise ValueError:
	# 	"""
	# 	layer = NS_FOREGROUND if type(layer) is None else layer
	# 	target = self._fetch_layer(layer)
	# 	try:
	# 		location_iter = iter(location)
	# 		if layer == NS_FOREGROUND:
	# 			target = self.foreground
	# 		elif layer == NS_BACKGROUND:
	# 			target = self.background
	# 		else:
	# 			raise TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")
	# 	except:
	# 		raise ValueError("Argument 'location' must be an iterable representation of  x, y coordinates.")
	#
	# 	return location[0] < target.shape[1] and location[1] < target.shape[0]

	# def region_in_layer_bounds(self, region, offset=0, layer=NS_FOREGROUND):
	# 	"""
	#
	# 	:param region:
	# 	:param offset:
	# 	:param layer:
	# 	:return: :raise TypeError:
	# 	"""
	# 	bounding_coords = [0, 0, 0, 0]  # ie. x1, y1, x2, y2
	# 	target = self._fetch_layer__(layer)
	# 	if type(offset) is int:
	# 		offset = (offset, offset)
	# 	elif type(offset) in (tuple, list) and len(offset) == 2 and all(type(i) is int and i > 0 for i in offset):
	# 		bounding_coords[0] = offset[0]
	# 		bounding_coords[1] = offset[1]
	#
	# 	if type(region) is Canvas:
	# 		bounding_coords[2] = region.width + offset[0]
	# 		bounding_coords[3] = region.height + offset[1]
	# 	elif type(region) is np.ndarray:
	# 		bounding_coords[2] = region.shape[1] + offset[0]
	# 		bounding_coords[3] = region.shape[0] + offset[1]
	# 	else:
	# 		raise TypeError("Argument 'region' must be either a numpy.ndarray or a klibs.Canvas object.")
	# 	in_bounds = True
	# 	for coord in bounding_coords:
	# 		in_bounds = self.location_in_layer_bounds(coord)
	#
	# 	return in_bounds


# def mask(self, mask, location=[0,0], grey_scale=False, layer=NS_FOREGROUND, auto_truncate=True):  # YOU ALLOW NEGATIVE POSITIONING HERE
	# 	"""
	#
	# 	:param mask:
	# 	:param location:
	# 	:param grey_scale:
	# 	:param layer:
	# 	:param auto_truncate:
	# 	:raise ValueError:
	# 	"""
	# 	if type(mask) is Canvas:
	# 		mask = mask.render()
	# 	elif type(mask) is str:
	# 		mask = import_image_file(mask)
	# 	elif type(mask) is not np.ndarray:
	# 		raise TypeError("Argument 'mask' must be a Canvas, numpy.ndarray or a path string of an image file.")
	# 	if grey_scale:
	# 		mask = grey_scale_to_alpha(mask)
	# 	if layer == NS_FOREGROUND:
	# 		self._content = copy(self.foreground)
	# 		self._foreground_mask__ = mask
	# 		self._ensure_writeable(NS_FOREGROUND)
	# 		if auto_truncate:
	# 			try:
	# 				iter(location)
	# 				location = [location[0], location[1]]
	# 			except AttributeError:
	# 				print("Argument 'location' must be iterable set of polar coordinates.")
	# 			new_pos = [0, 0]
	# 			mask_x1 = 0
	# 			mask_x2 = 0
	# 			mask_y1 = 0
	# 			mask_y2 = 0
	# 			# make sure location isn't impossible (ie. not off right-hand or bottom edge)
	# 			if location[0] >= 0:
	# 				if (mask.shape[0] + location[1]) > self.foreground.shape[0]:
	# 					mask_x1 = self.foreground.shape[0] - location[1]
	# 				else:
	# 					mask_x1 = 0
	# 				if mask.shape[1] + location[0] > self.foreground.shape[1]:
	# 					mask_x2 = self.foreground.shape[1] - location[0]
	# 				else:
	# 					mask_x2 = mask.shape[1] + location[0]
	# 				new_pos[0] = location[0]
	# 			else:
	# 				mask_x1 = abs(location[0])
	# 				if abs(location[0]) + mask.shape[1] > self.foreground.shape[1]:
	# 					mask_x2 = self.foreground.shape[1] + abs(location[0])
	# 				else:
	# 					mask_x2 = self.foreground.shape[1] - (abs(location[0]) + mask.shape[1])
	# 				new_pos[0] = 0
	#
	#
	# 			if location[1] >= 0:
	# 				mask_y1 = location[1]
	# 				if mask.shape[0] + location[1] > self.foreground.shape[0]:
	# 					mask_y2 = self.foreground.shape[0] - location[1]
	# 				else:
	# 					mask_y2 = mask.shape[0] + location[1]
	# 				new_pos[1] = location[1]
	# 			else:
	# 				mask_y1 = abs(location[1])
	# 				if abs(location[1]) + mask.shape[0] > self.foreground.shape[0]:
	# 					mask_y2 = self.foreground.shape[0] + abs(location[1])
	# 				else:
	# 					mask_y2 = self.foreground.shape[0] - (abs(location[1]) + mask.shape[0])
	# 				new_pos[1] = 0
	#
	# 			mask = mask[mask_y1: mask_y2, mask_x1: mask_x2]
	# 			location = new_pos
	#
	# 		elif self.region_in_layer_bounds(mask, location, NS_FOREGROUND):
	# 			self._fg_mask_pos__ = location
	# 		else:
	# 			raise ValueError("Mask falls outside of layer bounds; reduce size or relocation.")
	#
	# 		alpha_map = np.ones(mask.shape[:-1]) * 255 - mask[..., 3]
	# 		fg_x1 = location[0]
	# 		fg_x2 = alpha_map.shape[1] + location[0]
	# 		fg_y1 = location[1]
	# 		fg_y2 = alpha_map.shape[0] + location[1]
	# 		flat_map = alpha_map.flatten()
	# 		flat_fg = self.foreground[fg_y1: fg_y2, fg_x1: fg_x2, 3].flatten()
	# 		zipped_arrays = zip(flat_map, flat_fg)
	# 		flat_masked_region = np.asarray([min(x, y) for x, y in zipped_arrays])
	# 		masked_region = flat_masked_region.reshape(alpha_map.shape)
	# 		self.foreground[fg_y1: fg_y2, fg_x1: fg_x2, 3] = masked_region

	# def prerender(self):
	# 	"""
	#
	#
	# 	:return:
	# 	"""
	# 	return self.render(True)


	##
	# stub from former resize()
# try:
		# 	fg_clip = [output.shape[0] - (self.fg_offset[1] + self.foreground.shape[0]),
		# 			   output.shape[1] - (self.fg_offset[0] + self.foreground.shape[1])]
		# 	for clip in fg_clip:
		# 		axis = fg_clip.index(clip)
		# 		if clip >= 0:
		# 			fg_clip[axis] = self.foreground.shape[axis] + self.fg_offset[axis]
		#
		# 	new_bg = np.zeros((size[1], size[0], 4))
		# 	bg_clip = [new_bg.shape[0] - (self.bg_offset[1] + self.background.shape[0]),
		# 			   new_bg.shape[1] - (self.bg_offset[0] + self.background.shape[1])]
		# 	for clip in bg_clip:
		# 		if clip >= 0:
		# 			index = bg_clip.index(clip)
		# 			offset_index = 0 if index == 1 else 1
		# 			bg_clip[index] = self.background.shape[index] + self.bg_offset[offset_index]
		# except (AttributeError, IndexError):
		# 	raise ValueError("Argument dimensions must be a an iterable integer pair (height x width) ")
		#
		# # apply clipping if needed
		# self.foreground = self.foreground[0:fg_clip[0], 0:fg_clip[1]]
		# self.background = self.background[0:bg_clip[0], 0:bg_clip[1]]
		#
		# # insert old background and foreground into their positions on new arrays
		# y1 = self.bg_offset[1]
		# y2 = self.background.shape[0]
		# x1 = self.bg_offset[0]
		# x2 = self.background.shape[1]
		# new_bg[y1: y2, x1: x2, :] = self.background
		#
		# y1 = self.fg_offset[1]
		# y2 = self.foreground.shape[0]
		# x1 = self.fg_offset[0]
		# x2 = self.foreground.shape[1]
		# output[y1:y2, x1:x2, :] = self.foreground
		#
		# self.foreground = output
		# self.background = new_bg


	# self._update_shape()
	
#!/usr/local/bin/python3
from PIL import Image
import numpy as np

# Open input images, and make Numpy array versions


# Extract the RGB channels
fg_rgb = fg[...,:3]
bg_rgb = bg[...,:3]

# Extract the alpha channels and normalise to range 0..1
fg_alpha = fg[...,3]/255.0
bg_alpha = bg[...,3]/255.0

# Work out resultant alpha channel
comp_alpha = bg_alpha + fg_alpha*(1-bg_alpha)

# Work out resultant RGB
comp_rgb = (bg_rgb*bg_alpha[...,np.newaxis] + fg_rgb*fg_alpha[...,np.newaxis]*(1-bg_alpha[...,np.newaxis])) / comp_alpha[...,np.newaxis]

# Merge RGB and alpha (scaled back up to 0..255) back into single image
composite = np.dstack((comp_rgb, comp_alpha*255))
