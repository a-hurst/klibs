# Collecting Responses

Unless all your data of interest is being recorded independently by something like an eye tracker or EEG machine, you're probably going to want to collect responses to stimuli from your participants at some point in your experiment. The preferred way to do this in KLibs is to use **ResponseCollector** objects, one of which is provided for convenience during runtime as the Experiment attribute `self.rc`. There are several types of response you can collect in a KLibs experiment, some of which are not quite ready for public use, but this guide will give you the rundown of the most common and important ones and how to use them.

*Author's Note*: If this section seems a little complicated and overwhelming, that's because it *is* a little complicated and overwhelming. Bear with me, I'll do my best to provide worked examples throughout and avoid making things any more complex than they need to be. 

## What's a ResponseCollector?

A ResponseCollector is an object that simplifies the collecting of data from different input sources. A ResponseCollector contains one or more *listeners*, which are sub-objects that listen for certain types of responses (e.g. keyboard responses, audio responses, eye movement respones). There are two main parts of using a ResponseCollector: **setup**, which is done before a trial, and **collection**, which is done during a trial.

### Setting up a ResponseCollector

In your project's 'experiment.py' file, you might have noticed that there is an empty method called 'setup\_response\_collector'. This is run before 'trial\_prep' at the beginning of every trial of your experiment, and is where you can set things like the timeout for your response colletion period, the type(s) of responses to collect, and what function (if any) should be run every loop to draw the right stimuli to the screen. It's also where you configure the different response listeners you'll be using for that trial, such as setting which keys to watch if collecting a keypress response, or setting the colour wheel object to use for a color selection response.

To illustrate, let's take a look at the following code:

```python
def setup_response_collector(self):
    self.rc.uses(RC_KEYPRESS) # listen for keypress responses
    self.rc.terminate_after = [2000, TK_MS] # end collection loop after 2000ms
    self.rc.display_callback = self.resp_callback # run the self.resp_callback method every loop
    self.rc.flip = True # flip the screen at the end of every loop
    self.rc.keypress_listener.key_map = self.keymap # set keymap for experiment (defined elsewhere)
    self.rc.keypress_listener.interrupts = True # end collection loop if a valid key is pressed
```

The `self.rc.uses` method is used to define which response listeners should be used during the collection loop. The constants that correspond to the different types of responses are given below in the "response types" section. You can either pass a single response type to it as shown above, or you can pass a list of different response types (e.g. `self.rc.uses([RC_KEYPRESS, RC_AUDIO])`) and the ResponseCollector will check each of the corresponding listeners for input every loop during collection.

The `self.rc.terminate_after` attribute is used indicate the maximum amount of time that the ResponseCollector should wait for a response before exiting and moving on. This is given in the form of a List with two elements: the first being the number of time units to wait (e.g. 2000), and the second being either `TK_S` or `TK_MS`, to indicate whether your interval is in seconds or milliseconds, respectively. The constants `TK_S` and `TK_MS` are defined in the KLibs module 'KLConstants' and must be imported from there in your imports before they can be used in your experiment.

The `self.rc.display_callback` attribute is where you can set a function (specifically, a display callback) that will be run every collection loop just after all active response listeners have been checked for input. For example, if you wanted to brighten one of two boxes and get participants to respond as quickly as possible, you could have a function like this:

```python
def response_callback(self):
    # Note: self.target_loc and self.non_target_loc would be defined already during trial_prep

    fill() # fill the display buffer with a solid colour
    blit(self.fixation, 5, P.screen_c) # draw fixation at the center of the screen
    blit(self.bright_box, 5, self.target_loc) # draw the brightened box at the target location
    blit(self.box, 5, self.non_target_loc) # draw the regular box at the non-target location
    flip() # draw the contents of the display buffer to the screen
```

This would present these stimuli as soon as the collection loop started and would continue to present them until the collection loop ended (due to either a terminating response or timeout). The `self.rc.flip` attribute tells the ResponseCollector to flip the screen at the end of the display callback on each loop ('False' by default), and should only be set to 'True' if your display callback doesn't flip the screen itself. You can also pass arguments to your callback function if it takes any using the `self.rc.display_args` or `self.rc.display_kwargs` attributes, which let you pass argument values in the form of a List or a Dict, respectively. To illustrate, let's say your callback looked like this:

```python
def display_callback(self, draw_boxes=False, target=None):
    # code that always draws a fixation at the center of the screen, draws boxes on either side 
    # of the screen if 'draw_boxes' is True, and also draws a square target if target='square', 
    # a circle target if target='circle', or no target if target=None
```

if you wanted your collection loop to draw the boxes along with a circle target, you could set

```python
self.rc.display_args = [True, 'circle']
```
or 
```python
self.rc.display_kwargs = {'draw_boxes': True, 'target': 'circle'}
```
within setup\_response\_collector to achieve this. Note that the only meaningful difference between the two is that in the second one you specify the names of the arguments as well as their values, whereas in the first you only have to provide the argument values but they have to all be in the correct order. The choice is yours for which to use, so I'd recommend whichever you find produces the most readable code.

The last two lines of the example 'setup\_response\_collector' block configure the ResponseCollector's keypress listener. The `key_map` attribute is specific to the keypress listener and we'll discuss that more below, but the `interrupts` attribute is shared by all response listener types. If `interrupts` is set to True for a response listener, it means that a response from that listener will immediately end the collection loop. If `interrupts` is not set to True for at least one listener, the collection loop will continue until the timeout value set by `terminate_after` is reached. 

### Collecting data with a ResponseCollector

Once your ResponseCollector has been configured, collecting data is actually quite easy: all you need to do is call `self.rc.collect()` to run the response collection loop. Once the response loop has ended, you can use the `response()` method of the ResponseCollector's listeners to retrieve the response and reaction time values for each type of response you were collecting. 

By default the `response()` method returns both the response value and the reaction time for the previous collection loop in a Python list (in that order). Using a neat Python trick, you can assign the output of this function to separate 'response' and 'rt' variables like this:

```python
self.rc.collect() # run response collection loop
response, rt = self.rc.keypress_listener.response() # assign collected values to variables
```

What's happening here is that in Python, you can assign all the elements of a list to separate variables in the same line (e.g. `shape, size = ['square', 55]`), provided the number of variables on the left side of the equals sign matches the number of elements in the list. If you'd prefer to return *just* the response value or reaction time from the function, you can use the 'value' and 'rt' parameters of the function:

```python
response = self.rc.keypress_listener.response(rt=False) # get just the response value
rt = self.rc.keypress_listener.response(value=False) # get just the reaction time value
```

**Note on reaction times:** in KLibs, reaction times are determined by calculating the time between the moment the stimuli for the response collection loop are first presented and the time a response is first recorded. However, if your loop has a display callback it will be synced with the refresh rate of the screen (typically 16.7 ms per refresh, unless you have a special fancy monitor) meaning that collected responses can have up to ±17ms inaccuracy. Generally this doesn't end up being a huge problem during analysis but it's still something to keep in mind.

## Types of Response Listeners

As mentioned before, ResponseCollectors use one or more response listeners that listen for certain types of inputs. Here are the most common ones, with explanations of how they work and how to use them:

### Keypress Listener

```python
self.rc.uses(RC_KEYPRESS) # to enable listener
self.rc.keypress_listener # to access/configure listener
```

Most cognitive science experiments involve at least some input from the keyboard, such as pressing "z" to indicate a target was on the left side of the screen and "/" to indicate it was on the right side. The Keypress listener makes this pretty easy: once you've configured the timeout and display callback for the ResponseCollector, all you need to do is define a KeyMap object to tell it which keys to watch for input from.

To define a KeyMap for the Keypress listener to use, you first need to import the KeyMap object from KLKeyMap in your imports section, as well as the sdl2 module:

```python
 __author__ = "Your Name"

import klibs
from klibs import P
# ...
from klibs.KLKeyMap import KeyMap # add this line

import sdl2 # and this one
```

Then you can define a KeyMap object with the following structure, preferably within the setup block of your experiment:

```python
# Initialize ResponseCollector keymap
self.keymap = KeyMap(
    'target_response', # Name
    ['z', '/'], # UI labels
    ['left', 'right'], # Data labels
    [sdl2.SDLK_z, sdl2.SDLK_SLASH] # SDL2 Keycodes
)
```

Let's break that down a bit: the first two arguments are the *name* of the keymap and the *UI labels* (characters or plain English names of the keys being used). Neither of these really affect anything in this context, so just make sure they're informative to someone reading your code. 

The next argument is the *data labels* for the keys being used. When one of these keys is pressed during the collection loop, the response value returned will be the data label associated with the key (e.g. in this case, if you pressed 'z' during collection with the above keymap, the return value of `self.rc.keypress_listener.response(rt=False)` would be 'left'). 

The fourth and final argument for the KeyMap object are the *SDL2 Keycodes* that correspond to the keys you want to watch for input from. These are the unique identifiers that SDL2 uses internally for identifying individual keys on the keyboard. To figure out what keycodes correspond to the keys you want to use, you can use [the Keycode lookup table](https://wiki.libsdl.org/SDL_Keycode) in the official SDL2 docs. Note that the number of UI labels, data labels and keycodes all have to be equal and in the same order for the KeyMap to work properly.

Now, once you've defined your KeyMap, all you need to do is assign it to your ResponseCollector's keypress listener (assusimg you've already enabled the listener with `self.rc.uses()`):

```python
# within setup_response_collector(), after self.rc.uses
self.rc.keypress_listener = self.keymap
```

### Colour Selection Listener

```python
self.rc.uses(RC_COLORSELECT) # to enable listener
self.rc.color_listener # to access/configure listener
```

One of KLibs' most novel and interesting features is how easy it makes it to do experiments with colour wheels, which are often used in memory research and occasionally attention and perception research to measure how different factors affect people's accuracy at identifying a colour they had seen previously. 

Before you can use the colour selection listener, you first need to create a ColorWheel object using KLDraw, and a callback function that draws the colour wheel to the screen. You also need another KLDraw object, such as a dot (with the Ellipse drawbject) that you will use as a probe that will contain the target colour during trials:

```python
# within the imports section
from klibs.KLGraphics import KLDraw as kld # import drawing library
from klibs.KLUtilities import deg_to_px # import 'degrees of visual angle to pixels' function

# within 'setup'
wheel_size = int(P.screen_y * 0.75)
probe_size = deg_to_px(0.5)
self.wheel = kld.ColorWheel(diameter=wheel_size)
self.probe = kld.Ellipse(width=probe_size, fill=None)

# somewhere within the Experiment object
def wheel_callback(self):
	fill() # fill the display buffer with the default fill colour
	blit(self.wheel, registration=5, location=P.screen_c) # draw wheel to middle of screen
	flip() # draw contents of display buffer to screen

```

Then, in the 'setup\_response\_collector' section you need to enable the colour listener, set your display callback, and tell the listener what the wheel and probe objects are:

```python
def setup_response_collector(self):
    self.rc.uses(RC_COLORSELECT) # enable colour wheel responses
    self.rc.terminate_after = [8, TK_S] # break loop if no response after 8 seconds
    self.rc.display_callback = self.wheel_callback # set display callback
    self.rc.color_listener.set_wheel(self.wheel) # set your colour wheel object as the wheel to use
    self.rc.color_listener.set_target(self.probe) # set your probe as the object with the target color
```

The wheel and target objects are used during collection to determine which mouse clicks fall within the wheel and what the *degrees of angular error* are between the selected colour and the target colour on the wheel. Note that right now, our target object doesn't have a fill colour since we didn't give it one, but we'll give it one later during 'trial\_prep'. The colour used for the angular error calculations isn't the colour of the target at the time `set_target` is used but rather whatever colour the target object has when entering the response collection loop.

Now, the last things you need to do (apart from writing the code to show the target object at some point in the trial) are a) rotate the colour wheel by a random amount before entering the trial (to remove any possible location biases), and b) select a random colour from the wheel and set it as the fill for the target object. You should do this in trial\_prep, which gets run before every trial:

```python
# within the imports section
from random import randrange # builtin python function for selecting random numbers

# somewhere within 'trial_prep'
self.wheel.rotation = randrange(0, 360) # set wheel rotation to random angle between 0 and 359
self.wheel.render() # pre-render wheel object for speed
self.probe.fill = self.wheel.color_from_angle(randrange(0, 360)) # set fill to random color from wheel
self.probe.render() # pre-render wheel object for speed

```

#### Additional parameters

```python
self.rc.color_listener.warp_cursor = True
```
Warps the mouse cursor to the middle of the wheel at the start of the collection loop so that all colours are guaranteed to be equidistant from the mouse. True by default, but can be set to False to disable.

```python
self.rc.color_listener.angle_response = True
self.rc.color_listener.color_response = False
```
These parameters let you specify what kind of value you want the colour listener to return. If only `angle_response` is True (default), the response value will be the degrees of angular error between the angle of the target colour on the wheel and the angle of response. If only `color_response` is True, the response value will be the RGBA colour at the location the wheel that was clicked. If both are True, the response value will be a Tuple containing both degree of angular error and selected colour, in that order.


### Audio response listener

```python
self.rc.uses(RC_AUDIO) # to enable listener
self.rc.audio_listener # to access/configure listener
```

*Coming soon...*