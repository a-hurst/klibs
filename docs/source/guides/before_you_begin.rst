Before You Begin
================

What's Expected of You, The Author
----------------------------------
If you can't write a lick of code (specifically Python), you're not going to be able to use
KLIBs. KLIBs lets you leverage your skills to get more, and to get things done
faster. A hammer is only better than a rock if you already know all about nails.

Secondly, the KLIBs paradigm has a learning curve; not unlike a Windows user trying OS X for the first time, 
initially everything may seem arbitrarily different when compared with comparable modules, or even
the functionality from other modules that is wrapped by KLIBs. But, as with the Windows adopter of OS X, 
the hope is that the KLIBsian way of doing things will eventually feel refreshingly friendly and sane.

What KLIBs *Is*
---------------
KLIBs is a rapid development framework for writing experiments in Python. This means that
KLIBs provides a 'skeleton' of an experiment, and an extensive API for developing that 
skeleton into a proper experiment faster, or more efficiently, or more robustly than it
*might* otherwise have been done. Perhaps your experiment demands certain tools, frameworks,
libraries, etc. that make KLIBs a poor choice; perhaps you're so familiar with other tools 
that the learning curve exceeds the pay-off in terms of efficiency.

The goal of KLIBs is not replace the many modules it depends on, nor to be an entirely comprehensive
experiment-writing system. Rather, it attempts to wrap or abstract away the trickier parts 
of writing an experiment so novice programmers can get something done with minimal knowledge
and advanced programmers can get the busy work out of the way without having their hands tied.

KLIBs assumes the following:

- that experiments will be graphical in nature
- that experiments will follow a general pattern of trials that occur within blocks, sharing some set of factors
- the participants will make responses using their hands, eyes or voice
- that timing is important

Consider, then, that a PowerPoint presentation works on basically the same assumptions; presenting graphical 
information in sequence, and provides tools for creating that content. Indeed, there's no reason one 
couldn't implement their PowerPoint presentation in KLIBs. 


Some benefits of using KLIBs:

- it places *very* few constraints on the use of third party modules, frameworks, libraries. etc. 
- it provides a consistent, OS X-like user-interface (ie. command keys issue commands)
- user-friendly and internally consistent API for drawing, writing and otherwise manipulating the display
- it writes to a database, as against text files, which has a number of benefits discussed later
- conventions that result in rapid configuration regarding trial factoring, iteration, 

What KLIBs *Is Not*
-------------------
KLIBs is *not* an experiment creator. It doesn't write code for you, nor does it have
very much science built into it (almost none in fact, except for basic timing considerations).
It is not a way to avoid having to learn to program, and it knows nothing about experimental paradigms,
statistics, etc.. KLIBs is a tool for getting done more quickly those things you were already going to do.


Convention vs Configuration
---------------------------
Sometimes the power to have a fine degree of control is important; an example ill go here?
Other times, configurative options can be obfuscating and create a need to make decisions about, and anticipate
absurd combinatorial contexts that follow. KLIBs has been an effort to sweep into convention 
those things that can be and to leave exposed everything that needs, or may need, configuration. 

This means you will rarely be rail-roaded into anything by KLIBs, but it also means you can break it. The 
safest way to proceed will always be:
	
1. Stick to convention (where one exists) whenever you can
2. Understand the consequences of departing from convention before you do it, or be prepared to wrangle some code

As for these conventions themselves, read on to The KLIBs Paradigm


A Note For Experienced Developers
---------------------------------
When I started this project, I was an *extremely* novice programmer. There is absolutely legacy code
in the guts of this thing that would make me shudder, today. But iterative updating has routed out most of this.
Though I've tried to be as pythonic as possible, in some places ignorance will have led me astray, and in other
places I'll have made choices that are about facilitating the novice programmer's getting immediately to work. 
One particularly strange aspect of KLIBs is it's KLParams module, which, really, is a proper module that
gets terribly overwritten at runtime. This decision was made because it consolidates a great deal of global
variables *as well as* project-specific variables in one location, all with default values where appropriate. 
When you find these quirks of KLIBs, I encourage you to consider the experience of the intended user-base; novice
programmers who have no ambitions to become developers in their own right but whose academic progress requires them
to write code. KLIBs is for them, the people who were probably never going to do it all just right in the first place.
It's for taking some of the stress out of authoring a project ostensibly beyond themselves by housing a rudimentary but
ostensibly comprehensive toolkit under one roof. 