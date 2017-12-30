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

`self.oval = kld.Ellipse(self, width, height=None, stroke=None, fill=None, auto_draw=True)`
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
	blit(self.circle, 5, self.midleft)
	
	
	

### flip()

The `flip()` function takes the current contents of the display buffer (everything that has been blitted to the buffer since it was last cleared) and transfers them to the screen. The function will display the buffer contents until the screen is refreshed with `clear()` or `blit()`.

	blit(self.circle, 5, P.screen_c)
	flip()

### fill()

The `fill()` function fills the display buffer with a specified colour (defaults to `P.default_fill_color`, which is a light grey, if no colour specified). This function is used when you want to clear the display buffer (i.e. all blitted objects since last fill or clear) without clearing the screen as well.

### clear()

The `clear()` function clears both the display buffer and the display, replacing both with a specified colour (defaulting to `P.default_fill_color` if no colour specified). This is the equivalent of calling `fill()` to fill the buffer with a colour and subsequently `flip()` to transfer the contents of the buffer to the screen.

## Putting It Together

So, you want to get started drawing in KLibs? Thanks to how KLibs is written, it's very easy to get from a fresh project to drawing a shape on the screen. To get started, create a new project called 'DrawTest' using 'klibs create DrawTest' in the folder you want to put it in, then open the experiment.py file for the project. Then we need to import the KLDraw library so we can use its shapes, and the basic functions for working with the display buffer from KLGraphics. We'll also import the function 'any_key' to allow you to make the experiment wait for your input. To do all this, add the following lines to the top of your experiment.py file:

```python
__author__ = "Your Name"

import klibs
from klibs import P
from klibs.KLUserInterface import any_key # add this line
from klibs.KLGraphics import fill, blit, flip # and this one
from klibs.KLGraphics import KLDraw as kld # and also this one
	
```

Then, in the setup section of the experiment, assign a shape from KLDraw to a variable. For the purpose of this tutorial we'll use a colour wheel, because it's pretty:

```python
	# Note: make sure to remove the 'pass' line from a function after adding real content to it
    def setup(self):
		# Define wheel diameter as 75% of the height of the screen
		wheelsize = int(P.screen_y*0.75)
		# Create colour wheel object
        self.colour_wheel = kld.ColorWheel(diameter=wheelsize)
```

Note that we preface the colour wheel variable with the prefix 'self.'. This prefix is required whenever you want to use a variable defined in one function from other functions in the experiment object. For example, the variable 'wheelsize' is not prefaced with 'self.' here. If you tried to use that variable within the function trial() as-is, it would give you an error saying no such variable could be found. By using the 'self.' prefix, we make the varialbe an *attribute of the Experiment object*, meaning that we can access it from wherever.

Then, to actually draw the shape to the screen so you can see it, add the following lines to the 'trial' function:

```python
    def trial(self):
		# Fill the display buffer with the default fill colour (grey)
		fill()
		# Draw the colour wheel to the middle of the display buffer
        blit(self.colour_wheel, registration=5, location=P.screen_c)
		# Finally, draw the contents of the display buffer to the screen
		flip()
		# Lastly, wait for a keypress or click before continuing
		any_key()
```

Make sure to leave in the 'return' section at the end of the trial function, as the experiment will crash with an error without it.

Now, before you can run your experiment, you will need to add at least one independent variable to your independent_variables.py file in ExpAssets/Config/ (note: this will likely change soon, so that KLibs can launch with no independent variables set). For the purpose of this tutorial, you can add the following to the file:

```python
# Create an empty Independent Variable Set object
DrawTest_ind_vars = IndependentVariableSet()
# Add a varaible named "wheel_rotation" and an integer type to the set
DrawTest_ind_vars.add_variable("wheel_rotation", int)
# Add some angle values to the "wheel_rotation" variable
DrawTest_ind_vars["wheel_rotation"].add_values(0, 30, 60, 90, 120, 180)
```

The consequence of doing this, other than allowing your experiment to launch, is that the Experiment object attribute `self.wheel_rotation` will take on a value selected from the given list on every trial (you can learn more in the "Generating Trials" manual page). To test this out in this tutorial, you can replace the line 'pass' with the following lines in your experiment.py's trial_prep function:

```python
	def trial_prep(self):
		# Set the rotation of the colour wheel object to the trial's rotation value
		self.colour_wheel.rotation = self.wheel_rotation
		# Pre-render the wheel for faster blitting during runtime
		self.colour_wheel.render()
```

All done! Now, go to the root of your DrawTest experiment folder in a terminal window if you haven't already (e.g. "cd DrawTest") and then try running your project by using 'klibs run [screensize]', replacing [screensize] with the size of your monitor in diagonal inches (e.g. on a 13" MacBook Pro, you would type 'klibs run 13'). This will start the klibs experiment runtime, and after you see the KLibs logo and press any key, you should see a nicely rendered colour wheel that changes rotation every time you press a key on your keyboard.

!(DrawTest Colour Wheel)[resources/drawtest_colwheel.png]

Well done! You're getting a hang of things already. To quit an experiment once it's launched, you can use either Command-Q on a Mac or Control-Q or Alt-Q on Linux to quit the experiment gracefully. 

You'll notice that the experiment exits itself after a couple key presses. This is because by default, KLibs will run a single block of *n* trials, with *n* being the product of the number of different possible factors (in this case, we have 1 factor with 6 possible values, so 6 trials). You can manually set the number of blocks and trials per block in the params.py file in ExpAssets/Config. 

**Python Protip:** while launching your experiment for the first time, you may have gotten an error like this:

```
  File "experiment.py", line 38
    flip()
    ^
IndentationError: unexpected indent
  File "/usr/local/bin/klibs", line 281, in run
    experiment_file = imp.load_source(path, "experiment.py")
```
This is because Python as a language is super-picky about whether you use tabs or spaces to indent lines because indentation is how you indicate that a loop has started or ended and many other things. If you copy and paste lines of code from the internet into a Python file you've written, it may use a different kind of indentation and confuse the Python interpreter. To avoid this, most text editors have a "convert tabs to spaces" or "convert spaces to tabs" function you can use to make it all consistent. It doesn't matter which one you use (tabs or spaces, that is, but spaces is recommended by the official PEP8 style guide), the important thing is consistency.