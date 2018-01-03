# Managing the Event Manager

Okay, so by now you've probably learned how to draw things and generate trial factors in KLibs. Your question now is probably: "how do I make things happen in the order I want them to?" 

You *could* use the time-honoured tradition of using Python's time.time() function to count down each time interval in your project, but that's not terribly flexible and often leads to messy and code that's difficult to read and maintain. The KLibs-ian way to handle event sequencing is through a built-in module known as the **Event Manager**, which lets you lay out your whole sequence of events in the same block of code, and write easily readable loops to program the onsets and offsets of all your stimuli.

As part of the KLibs runtime, an EventManager object is automatically created for you and assigned to your Experiment object as the attribute `self.evm`. I'll explain a bit more about how it works at a low level later, but right now let's focus on how to use it in practice.

First, you need to add the following line to your imports at the top of your experiment.py file:

```python
from klibs.KLEventInterface import TrialEventTicket as ET
```

TrialEventTicket objects are used to denote the key events that occur within a trial, and take two arguments: a name, and a time. Then, these tickets are added to the EventManager before the start of the trial using the `register_ticket` method. Here, we import the object as the name `ET` for the sake of convenience because TrialEventTicket is a bit wordy.

```python
event = ET('cue_on', 1000) # Event 'cue on', which occurs 1000ms into the trial
self.evm.register_ticket(event) # add 'cue on' event to event manager
```

If you have many events to register, an easier way to do it would be to create a List object of all the events, and then register all those events with the EventManager using a loop, alike so:

```python
events = [] # create an empty list for all trial events
events.append([1000, 'cue_on']) # cue comes on 1000ms after start of the trial
events.append([events[-1][0] + 100, 'cue_off']) # cue comes off 100ms after the previous event
events.append([events[-2][0] + 500, 'target_on'] # 500ms after cue appears, target appears
for e in events:
    self.evm.register_ticket(ET(e[1], e[0]))
```

Note that there are two big advantages of doing it this way: first, all your events are grouped together in a single, readable block of code. In the wake of the replication crisis and the Open Science movement, writing code that total strangers can make sense of is increasingly important, and it's better to be part of the solution than the problem. Second, as you may have noticed in the lines for the 'cue\_off' and 'target\_on' events, you can set the timing of events relative to the timing of previous ones. For example, `events[-1][0] + 100` accesses the first element (i.e. the time) of the previous event (in this case, 1000ms) and adds 100ms to it, so if you decide to change the cue onset to 500ms instead, the cue off event will become 600ms along with it.

### Using defined events

Right, so we've defined the timing and names of the events we want to happen on a given trial in our experiment. Now how do we use these in a trial to make stuff happen?

The EventManager has 3 methods that can do almost everything you need, all of which return a simple True or False that can be used with `while` and `if` statements: before, after, and between. For example, to check in your code to see if the 'cue\_on' event has happened, you would use

```python
if self.evm.after('cue_on'):
    # do something
```

For a more complete example of how you might use the event tickets added to the EventManager in the previous section, see the code below:

```python
# the trial code for everything before target onset in a Posner cueing paradigm
while self.evm.before('target_on', pump_events=True):
    
    # fill display buffer with the default color and draw boxes and fixation
    # note: shapes and left and right locations would be defined already in setup()
    fill()
    blit(self.fixation, 5, P.screen_c)
    blit(self.box, 5, self.left_loc)
    blit(self.box, 5, self.right_loc)
    
    if self.evm.between('cue_on', 'cue_off'):
        # if it's currently between the cue on and cue off events, draw cue
        blit(self.cue_box, 5, self.cue_loc)
        					
    flip() # draw contents of display buffer to screen
```

Until the 'target\_on' event you registered with the EventManager earlier occurs at 1500ms into the trial, a fixation cross and two boxes (one on the left and one on the right) are drawn at predefined places to the screen. between the 'cue\_on' event at 1000ms and the 'cue\_off' event at 1100ms, a brighter box is drawn over top of one of the two placeholder boxes (the location of which is generally determined earlier in the code, in the trial\_prep function). 

You'll notice that the 'before', 'after', and 'between' methods have a flag called 'pump\_events'. This calls the ui\_request function every time the method is called, which ensures that any 'quit' or 'calibrate eyetracker' keypresses during the loop will be processed. This is convenient but can also be quite dangerous: every time ui\_request is called without an event queue passed to it, it pumps (i.e. fetches and empties) the event queue itself. "What's an event queue", you might ask? Well, when you press a key, or move/click the mouse, these are recorded as 'events' by SDL2 (the underlying input library that KLibs uses) that are put into a queue as soon as they occur. When you pump the queue using the 'pump()' function, it removes those events from the queue and returns them in a list so that they can be inspected. If you pump the event queue multiple times in a loop it can cause very frustrating and hard to debug issues with checking for input or using the TryLink EyeLink emulation module (and can also cause unexpected performance issues), so make sure not to set 'pump\_events' to True for more than one EventManager statement per loop.