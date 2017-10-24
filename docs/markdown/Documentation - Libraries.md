# KLibs Libraries

Like most Python frameworks, the components of KLibs are divided into several modules called libraries. The advantage of this modular approach is that *insert some explanation here*. Below is a list of the modules available in KLibs and their functions:

_**TODO: divide into sections based on most important/common, sometimes used by end user but not as common, and libraries (packages) mainly intended for internal use**_


## Common usage

## Special usage

## Internal use

### KLAudio

KLAudio is the library responsible for generating sounds, playing sound clips, and working with audio input. 

### KLBoundary

There are many cases in which we are interested in whether a given point is within a certain region. For example, we might want to check if one's gaze during an Eye Tracking experiment has landed in an area of interest, or we might want to check if the mouse cursor is hovering over a button before we highlight it.  

KLBoundary defines boundary objects (which can be rectangular, circular, or in the form of an annulus), along with functions for checking whether a given pixel coordinate is within a specified boundary.

### KLCommunication

KLCommunication is the library that deals with displaying messages to users and querying text responses from users. This includes demographics collection (which is done automatically when not in `P.development_mode` and `P.manual_graphics_collection` is not enabled), prompting users for text input, and rendering short strings of text for display to users (e.g. block messages, instructions, response feedback).

In addition, KLCommunication also provides a Slack messaging feature which, when properly configured, allows your experiment program to send messages to a Slack channel of your choice at certian points in your code. This feature is intended for running experiments in labs where the experimenter is in a different room from the participant, so that the researchers or RAs running subjects can be informed of a participant's progress and thus be better able to plan their own time (e.g. know if the participant is in the last block of the experiment so they know whether to run and get lunch or not). This feature can also be used as a means for participants to notify reserachers if they need assistance at any point by mapping a slack message to a "alert researcher" key on the keyboard.

*should have page on setting up the slack messaging system*

### KLConstants

KLConstants defines a large number of constants, many of which are intended for internal use by KLibs, but some of which are quite useful for making easily readable code. Notable groups of constants intended for end-user use are the ones defining the codes for EyeLink event types (e.g. `EL_SACCADE_END` is the return value for Saccades in the EyeLink API), and the types of Response Collector.

### KLDatabase

KLDatabase is the component of KLibs responsible for working with the database that stores all your data. 

In most simple cases your trial data will be written to the database without you needing to interface with KLDatabase directly, but if you want to collect data in one or more seperate tables in your database during your experiment (e.g. if you want to collect eye event data separately from trial repsonse data) you will need to use KLDatabase's `insert()` function to do so. 

A KLibs experiment automatically initiates a Database connection at launch and makes the instance available as `self.db`, so you will typically not need to import KLDatabase into your project.

### KLDebug

### KLDraw

KLDraw is a library for drawing stimuli, and contains a number of functions to create various shapes useful for cognitive psychology research (e.g. lines, rectangles, fixation crosses, colour wheels). 

### KLEDFParser

### KLEnvironment

KLEnvironment is for internal use only, and serves to make instances of important classes globally accessable across a KLibs environment. 

It imports an EventManager instance, an Experiment instance, a Database instance, a TextManager instance, a TimeKeeper instance, a ResponseCollector instance, and an EyeLink instance (if the `P.eyetracking` variable is set to 'True'). Consequently, none of the above classes should ever need to be imported manually.

### KLEventInterface

### KLExceptions

KLExceptions defines a number of exception types used internally in KLibs. For the end user, the most important one by far is `TrialException`, which, if thrown or raised at any time during a trial, will result in the trial being immediately ended and its factor set being recycled into the list of remaining trials for that block.

### KLExperiment

### KLEyeLink

### KLIndependentVariable

### KLJSON_Object

KLJSON_Object is a class largely intended for internal use, which serves to allow the importing of properly formatted .json files into objects that can then be manipulated in code. 



### KLKeyMap

### KLLabJack

KLLabJack provides a simple interface for working with LabJack U3 data acquisition devices within KLibs experiments. It requires the `LabJackPython` library to be installed in order to operate, which can be installed with `pip install LabJackPython`.

### KLNamedObject

### KLParams

### KLResponseCollectors

### KLText

### KLTime

### KLTrialFactory

### KLUserInterface

KLUserInterface is the component of KLibs that deals with user input outside of response collection. At present, it has two primary functions: 

The first, `any_key()`, is for pausing code execution until a key on the keyboard is pressed. 

The second, `ui_request()`, is for checking if any special key combinations have been pressed since last check (e.g. Command-Q to quit the experiment). Many functions call ui_request automatically, meaning that you will only need to use it yourself in situations where you are creating a loop during which you would like the ability to quit the experiment.

### KLUtilities