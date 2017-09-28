# Drawing in KLibs

Before drawing anything in a KLibs experiment, you first need to understand that KLibs uses what's known as the __painter's model__ for drawing. What this means is that objects can be continuously drawn on top of other objects in a KLibs experiment (just like paint can be added on top of existing paint on a canvas), but existing objects can't be removed individually. Instead, removing an individual object is done by refreshing the screen (starting with a fresh canvas) and redrawing all objects except those  you want removed.

Clearing the screen of existing objects is accomplished by `clear()`

__TODO: introduce concept of display buffer__

In addition, rendering (the creation of an object) and displaying objects are accomplished by separate functions. To display all rendered objects to the screen, you can use flip().

## Drawable Objects in KLDraw

In KLibs, several types of objects can be easily drawn. The following examples assume that KLDraw has been imported in the main experiment.py document using:

`import klibs.KLGraphics.KLDraw as kld`


### Annulus

The annulus class creates a ring object with a specified diameter, *width, *stroke, and fill.

`self.ring = kld.Annulus(self, diameter, ring_width, stroke=None, fill=None, auto_draw=True)`
### Bezier

The Bezier class creates a curved line object (how does it work?)

`self.bezier = kld.Bezier(self, height, width, origin, destination, ctrl1_s, ctrl1_e, ctrl2_s=None, ctrl2_e=None, stroke=None, fill=None, auto_draw=True)`
### Ellipse

The Ellipse class creates an oval object with a specified width, height, stroke, and fill. If height is not specified, it defaults to the same value as width and creates a circle.

`self.oval = kld.Circle(self, width, height=None, stroke=None, fill=None, auto_draw=True)`
### Line

The Line class creates a straight line object of a specified length, colour, thickness, and rotation.

`self.line = kld.Line(self, length, color, thickness, rotation=0, pts=None, auto_draw=True)`
### Rectangle

The Rectangle class creates a rectangle object with a specified width, height, stroke, and fill colour. If height is not specified it will default to the value for width, creating a square.

`self.rect = kld.Rectangle(self, width, height=None, stroke=None, fill=None, auto_draw=True)`

### Fixation Cross

The FixationCross class creates a fixation cross object of a specified size, thickness, stroke, and fill.

`self.fixation = kld.FixationCross(self, size, thickness, stroke=None, fill=None, auto_draw=True)`

### Asterisk

The Asterisk class creates an asterisk object of a specified size, colour, and stroke.

`self.asterisk = kld.Asterisk(self, size, color, stroke=1, auto_draw=True)`

### Color Wheel (should be ColourWheel?)

The ColorWheel class creates an RGB colour wheel object with a specified diameter, thickness, and rotation.

`self.rgb_wheel = kld.ColorWheel(self, diameter, thickness=None, rotation=0, auto_draw=True)`

### FreeDraw

???

`self.freedraw = kld.FreeDraw(self, width, height, stroke, origin=None, fill=None, auto_draw=True)`
  
## Object Properties

As you can see from the above object prototypes, there are many properties that are most objects have in common. 

### Colour

In KLibs, the fill and stroke colours for objects are specified using RGB decimal code, with an extra optional integer to specify opacity. The format of a colour is thus `[R,G,B,O]`, indicating the desired values of Red, Green, Blue, and Opacity (if no opacity value is specified, it will default to 100%). You can use [an online utlility](http://www.rapidtables.com/web/color/RGB_Color.htm) to find the decimal code for the colour you want. Here are some example codes for some common colours:

	Black = [0,0,0]
	White = [255,255,255]
	Mid-Grey = [128,128,128]
	Red = [255,0,0]
	Blue = [0,255,0]
	Green = [0,0,255]
	Yellow = [255,0,255]
	Purple = [255,255,0]

As an example, if you wanted to draw a red square 100 pixels wide with a 50% opacity, you would use

	self.rect = kld.Rectangle(100, fill=[255,0,0,128])
	
Note that if you want to use a colour more than once in your experiment, you can save considerable time by defining it [where?] in your experiment.py file. For example, instead of writing

	self.rect = kld.Rectangle(100, fill=[128,128,128])
	self.fixation = kld.FixationCross(25, 5, fill=[128,128,128])

you could write
	
	GREY = [128,128,128]
	
	self.rect = kld.Rectangle(300, fill=GREY)
	self.fixation = kld.FixationCross(50, 5, fill=GREY)
	
In addition to saving you time and making your experiment code easier to read, the other advantage of defining your colours and calling them by name is that if you decide to change a colour later, all you need to do is change the definition and the colour will be changed throughout.

### Stroke

If you look back at the list of drawable object types in KLDraw, you will note that you are able to define a stroke (outline) for most of them. In KLDraw, stroke definitions follow the format of [width, colour, alignment], with width being in pixels and colour being in the RGB format explained above. Alignment refers to whether the stroke should be drawn inside, in between, or outside of the border of the shape, indicated by the values `1`, `2`, and `3`, respectively (alternatively, if you add `from klibs import KLConstants` to the top of your experiment file, you can use `STROKE_INNER`, `STROKE_CENTER`, and `STROKE_OUTER` in place of these numbers to produce more readable code).

For example, if you wanted to create a square 150 pixels wide with no fill and a white inner stroke with a width of 10 pixels , you would use
	
	self.square = kld.Rectangle(150, stroke=[10, [255,255,255], 1])
or, for improved readability,
	
	from klibs import KLConstants # At the top of the experiment.py file
	WHITE = [255,255,255]
	...
	self.square = kld.Rectangle(150, stroke=[10, WHITE, STROKE_INNER])
	
### Height And Width

By default, KLibs uses pixels as its primary unit of measurement. For instance, to draw a colour wheel with a diameter of 500 pixels, you would write
	
	self.colour_wheel = kld.ColorWheel(500)
	
You can also easily substitute degrees of visual angle in place of pixels when specifying the sizes of objects by using the `deg_to_px()` function from the KLUtilities library (imported into your experiment by adding `from klibs import KLUtilities` to experiment.py). _This conversion is possible because KLibs calculates the pixels per inch of your screen when it launches and assumes a distance of 57 cm from the display_. As an example, if you wanted to draw a colour wheel with a diameter of 7.5° of visual angle, you would use
	
	self.colour_wheel = kld.ColorWheel(deg_to_px(7.5))
	
An advantage of using degrees of visual angle in place of pixels when writing experiments is that stimuli will be drawn at roughly the same size and distance from eachother relative to the participant, regardless of screen size or seating distance, as long as you tell KLibs what these values are.

	
## Drawing Objects To The Screen

As discussed earlier, drawing objects to the screen is done using two functions: `blit()`, `flip()`, and `fill()`. "Blitting" is the process of taking something to be shown on the screen and rendering it (i.e. preparing it to be displayed), "flipping" is the process of displaying rendered objects on the screen, and "filling" fills a canvas with a given colour, and is usually done before `blit()` functions are called. All of these functions are imported from the `klibs.KLGraphics` module.

### blit()

In order to draw an object to the screen, it must first be blitted, which renders an object and writes it to the display buffer. The `blit()` function takes three values. See the below example of blitting a circle to the center of the screen:  

	blit(self.circle, 5, P.screen_c)  

The first value passed to the function is the name of the object to be blitted, in this case a circle named `self.circle`.  

The second value is the anchor point on the object, specifed by a number from `1` to `9` relative to the number pad on a keyboard. For instance, since `7` is the top-left number on the number pad, this specifes to the blit function that the anchor point for the blitted object should be its top left corner. In this case we want the circle centered in the middle of the screen, so we use `5` to place the anchor point in the center of the object.  

The third value is the location on the screen (in X/Y pixel coordinates) that the object should appear, relative to its anchor point as specified in the second value. KLibs automatically calculates the the coordinates for the center of the screen and saves them to `P.screen_c`, so to make things easy we can speficy this as the location for the circle to appear. The easiest way of drawing objects to places other than the center is to use P.screen_x and P.screen_y, which are the width and height, respectively, of the current display as measured in pixels from the top-left corner of the screen. If you wanted to draw a circle to the mid-left side of the screen you could use

	self.midleft = (P.screen_x / 4, P.screen_y / 2)
	clear(self.circle, 5, self.midleft)
	
	
	

### flip()

The `flip()` function takes the current contents of the display buffer (everything that has been blitted to the buffer since it was last cleared) and transfers them to the screen. It accepts one value, duration, which must be an integer greater than zero specifying the number of seconds for which the buffer contents should be shown on the screen. If no duration value is given, the function will display the buffer contents until the screen is refreshed with `clear()` or `blit()`.

For example, to display the circle rendered in the previous example on the screen for 50 ms, you would use  

	blit(self.circle, 5, P.screen_c)
	fill(0.050)
	
Note that timing using the flip() function is not incredibly accurate and should thus not be used in situations when the timing of events is important (e.g. cue/target duration, stimulus onset asynchrony). The Event timer from KLEventInterface should be used instead.


	
_Are there constants for common blit locations? (e.g. middle-left, top-right, etc.) Is it supposed to remove everything that was on the screen already?_

### fill()

The `fill()` function fills the display buffer with a specified colour (defaults to `P.default_fill_color`, which is a light grey, if no colour specified). This function is used when you want to clear the display buffer (i.e. all blitted objects since last fill or clear) without clearing the screen as well.

### clear()

The `clear()` function clears both the display buffer and the display, replacing both with a specified colour (defaulting to `P.default_fill_color` if no colour specified). This is the equivalent of calling `fill()` to fill the buffer with a colour and subsequently `flip()` to transfer the contents of the buffer to the screen. (?)

##Putting It Together
