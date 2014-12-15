__author__ = 'jono'
import pylink
import array
from AudioClip import AudioClip
from numpy_surface import *
from utility_functions import *
import time


class EyeLinkCoreGraphicsKL(pylink.EyeLinkCustomDisplay):
	__eyelink_key_translations = {
		"left": pylink.CURS_LEFT,
		"right": pylink.CURS_RIGHT,
		"up": pylink.CURS_UP,
		"down": pylink.CURS_DOWN,
		"return": pylink.ENTER_KEY,
		"space": sdl2.SDLK_SPACE
		# "a": sdl2.SDLK_a,
		# "c": sdl2.SDLK_c,
		# "o": sdl2.SDLK_o,
		# "v": sdl2.SDLK_v
	}

	def __init__(self, app, tracker):
		self.app = app
		self.size = self.app.window.size
		self.tracker = tracker
		self.fill_color = (128, 128, 128, 255)
		if sys.byteorder == 'little':
			self.byteorder = 1
		else:
			self.byteorder = 0

		pylink.EyeLinkCustomDisplay.__init__(self)

		try:
			self.__target_beep__ = AudioClip("target_beep.wav")
			self.__target_beep__done__ = AudioClip("target_beep_done.wav")
			self.__target_beep__error__ = AudioClip("target_beep_error.wav")
		except:
			self.__target_beep__ = None
			self.__target_beep__done__ = None
			self.__target_beep__error__ = None

		self.imagebuffer = array.array('L')

		"""
		unknown var
		"""
		self.pal = None
		# self.cal_vp = Viewport(screen=cal_screen, stimuli=[target])
		#
		# # Create viewport for camera image screen
		# text = Text(text="Eye Label",
		#    		color=(0.0,0.0,0.0), # alpha is ignored (set with max_alpha_param)
		#    		position=(cal_screen.size[0]/2,int(screen.size[1]*0.1)),
		#    		font_size=20,
		#    		anchor='center')
		#
		#
		# img =Image.new("RGBX",(int(screen.size[0]*0.75),int(screen.size[1]*0.75)))
		# image = TextureStimulus(mipmaps_enabled=0,
		# 	   texture=Texture(img),
		# 	   size=(int(screen.size[0]*0.75),int(screen.size[1]*0.75)),
		# 	   texture_min_filter=gl.GL_LINEAR,
		# 	   position=(cal_screen.size[0]/2.0,cal_screen.size[1]/2.0),
		# 	   anchor='center')
		#
		# self.image_vp = Viewport(screen=cal_screen, stimuli=[text,image])

		self.width = Params.screen_x
		self.height = Params.screen_y

	def setup_cal_display(self):
		print "setup_cal_display()"
		self.window = sdl2.ext.Window("Calibration", size=Params.screen_x_y, position=(0, 0), flags=SCREEN_FLAGS)
		self.window_id = sdl2.SDL_GetWindowID(self.window.window)
		self.window_surface = sdl2.SDL_GetWindowSurface(self.window.window)
		self.window_array = sdl2.ext.pixels3d(self.window_surface.contents)
		self.clear_cal_display()
		time.sleep(0.1)
		sdl2.SDL_PumpEvents() #to show the windows

	def exit_cal_display(self):
		print "exit_cal_display()"
		sdl2.SDL_DestroyWindow(self.window.window)

	def record_abort_hide(self):
		print "record_abort_hide()"
		pass

	def clear_cal_display(self):
		print "clear_cal_display()"
		r, g, b, a = self.fill_color
		sdl2.ext.fill(self.window_surface.contents, sdl2.pixels.SDL_Color(r, g, b, a))
		self.window.refresh()
		sdl2.ext.fill(self.window_surface.contents, sdl2.pixels.SDL_Color(r, g, b, a))
		sdl2.SDL_PumpEvents()

	def erase_cal_target(self):
		print "erase_cal_target()"
		self.app.fill(self.fill_color)
		self.app.flip()

	def draw_cal_target(self, location):
		print "draw_cal_target(): {0}".format(location)
		draw_context_length = Params.screen_x // 70
		black_brush = aggdraw.Brush(tuple(0, 0, 0, 255))
		white_brush = aggdraw.Brush(tuple(255, 255, 255, 255))
		draw_context = aggdraw.Draw("RGBA", [draw_context_length, draw_context_length], (0, 0, 0, 0))
		draw_context.ellipse([0, 0, draw_context_length, draw_context_length], black_brush)
		draw_context.ellipse([0, 0, draw_context_length // 2, draw_context_length // 2], white_brush)
		# x1 = draw_context_length // 2
		# y1 = draw_context_length // 5
		# x2 = x1
		# y2 = draw_context_length - y1
		# stroke = draw_context_length // 5
		# draw_context.line([x1, y1, x2, y2], pen)
		# draw_context.line([y1, x1, y2, x2], pen)
		self.app.blit(from_aggdraw_context(draw_context), 5, location)

	def play_beep(self, clip):
		print "play_beep(): {0}".format(clip)
		if clip == pylink.DC_TARG_BEEP or clip == pylink.CAL_TARG_BEEP:
			self.__target_beep__.play()
		elif clip == pylink.CAL_ERR_BEEP or clip == pylink.DC_ERR_BEEP:
			self.__target_beep__error__.play()
		else:
			self.__target_beep__done__.play()

	def get_input_key(self):
		print "get_input_key()"
		key = self.app.listen(MAX_WAIT, "eyelink", flip=False)[0]
		input_key = self.__eyelink_key_translations[key] if key in self.__eyelink_key_translations else 0
		print "Input Key: {0}".format(input_key)
		return input_key

	def get_mouse_state(self):
		print "get_mouse_state()"
		return mouse_pos()

	def exit_image_display(self):
		print "exit_image_display()"
		self.app.clear(self.fill_color)
		self.app.flip()

	def alert_printf(self, message):
		print "alert_printf(): message -> {0}".format(message)
		self.app.message(message, color=(255, 0, 0, 0), location=(0.05 * Params.screen_x, 0.05 * Params.screen_y))

	def setup_image_display(self, width, height):
		print "setup_image_display(): width -> {0}, heigh -> {1}".format(width, height)
		self.img_size = (width, height)
		self.image_vp.parameters.screen.clear()
		pass

	def image_title(self, text):
		print "image_title(): text -> {0}".format(text)
		# self.image_vp.parameters.stimuli[0].parameters.text=text
		pass

	def draw_image_line(self, width, line, totlines, buff):
		print "draw_image_line(): width -> {0}, line -> {1}, totlines -> {2}, buff -> {3}".format(width, line, totlines, buff)
		# i = 0
		# while i <width:
		# 	if buff[i]>=len(self.pal):
		# 		buff[i]=len(self.pal)-1
		# 	self.imagebuffer.append(self.pal[buff[i]&0x000000FF])
	     #            #self.imagebuffer.append(self.pal[buff[i]])
		# 	i= i+1
		#
		# if line == totlines:
		# 	img =Image.new("RGBX",self.img_size)
		# 	img.fromstring(self.imagebuffer.tostring())
		# 	img = img.resize(self.image_vp.parameters.stimuli[1].parameters.size)
		#
		# 	self.__img__=img
		# 	self.draw_cross_hair()
		# 	self.__img__=None
		# 	self.image_vp.parameters.stimuli[1].texture_object.put_sub_image(img)
		#
		# 	self.image_vp.parameters.screen.clear()
		# 	self.image_vp.draw()
		#
		# 	VisionEgg.Core.swap_buffers()
		#
		# 	self.imagebuffer = array.array('l')
		pass

	def draw_lozenge(self, x, y, width, height, colorindex):
		print "draw_lozenge(): x -> {0}, y -> {1}, width -> {2}, height -> {3}, colorindex -> {4}".format(x, y, width, height, colorindex)
		pass
		# if colorindex   ==  pylink.CR_HAIR_COLOR:          color = (255,255,255,255)
		# elif colorindex ==  pylink.PUPIL_HAIR_COLOR:       color = (255,255,255,255)
		# elif colorindex ==  pylink.PUPIL_BOX_COLOR:        color = (0,255,0,255)
		# elif colorindex ==  pylink.SEARCH_LIMIT_BOX_COLOR: color = (255,0,0,255)
		# elif colorindex ==  pylink.MOUSE_CURSOR_COLOR:     color = (255,0,0,255)
		# else: color =(0,0,0,0)
		#
		#
		#
		# imr = self.__img__.size
		# x=int((float(x)/float(self.img_size[0]))*imr[0])
		# width=int((float(width)/float(self.img_size[0]))*imr[0])
		# y=int((float(y)/float(self.img_size[1]))*imr[1])
		# height=int((float(height)/float(self.img_size[1]))*imr[1])
		#
		# idraw = PIL.ImageDraw.Draw(self.__img__)
		# if width>height:
		# 	rad = height/2
		#
		# 	#draw the lines
		# 	idraw.line([(x+rad,y),(x+width-rad,y)],fill=color)
		# 	idraw.line([(x+rad,y+height),(x+width-rad,y+height)],fill=color)
		#
		# 	#draw semicircles
		# 	clip = (x,y,x+height,y+height)
		# 	idraw.arc(clip,90,270,fill=color)
		#
		#
		# 	clip = ((x+width-height),y,x+width,y+height)
		# 	idraw.arc(clip,270,90,fill=color)
		#
		# else:
		# 	rad = width/2
		#
		# 	#draw the lines
		# 	idraw.line([(x,y+rad),(x,y+height-rad)],fill=color)
		# 	idraw.line([(x+width,y+rad),(x+width,y+height-rad)],fill=color)
		#
		# 	#draw semicircles
		# 	clip = (x,y,x+width,y+width)
		# 	idraw.arc(clip,180,360,fill=color)
		#
		#
		# 	clip = (x,y+height-width,x+width,y+height)
		# 	idraw.arc(clip,360,180,fill=color)




	def draw_line(self, x1, y1, x2, y2, colorindex):
		print "draw_line(): x1 -> {0}, y1 -> {1}, x2 -> {2}, y2 -> {3}, colorindex -> {4}".format(x1, y1, x2, y2, colorindex)
		# imr = self.__img__.size
		# x1=int((float(x1)/float(self.img_size[0]))*imr[0])
		# x2=int((float(x2)/float(self.img_size[0]))*imr[0])
		# y1=int((float(y1)/float(self.img_size[1]))*imr[1])
		# y2=int((float(y2)/float(self.img_size[1]))*imr[1])
		# idraw = PIL.ImageDraw.Draw(self.__img__)
		# if colorindex   ==  pylink.CR_HAIR_COLOR:          color = (255,255,255,255)
		# elif colorindex ==  pylink.PUPIL_HAIR_COLOR:       color = (255,255,255,255)
		# elif colorindex ==  pylink.PUPIL_BOX_COLOR:        color = (0,255,0,255)
		# elif colorindex ==  pylink.SEARCH_LIMIT_BOX_COLOR: color = (255,0,0,255)
		# elif colorindex ==  pylink.MOUSE_CURSOR_COLOR:     color = (255,0,0,255)
		# else: color =(0,0,0,0)
		# idraw.line([(x1,y1),(x2,y2)], fill=color)
		pass




	def set_image_palette(self, r, g, b):
		print "set_image_palette(): r -> {0}, g -> {1}, b -> {2}".format(r, g, b)
		# self.imagebuffer = array.array('L')
		# self.clear_cal_display()
		# sz = len(r)
		# i =0
		# self.pal = []
		# while i < sz:
		# 	rf = int(b[i])
		# 	gf = int(g[i])
		# 	bf = int(r[i])
		# 	if self.byteorder:
		# 		self.pal.append((rf<<16) | (gf<<8) | (bf))
		# 	else:
		#                    self.pal.append((bf<<24) |  (gf<<16) | (rf<<8)) #for mac
		# 	i = i+1
		pass
