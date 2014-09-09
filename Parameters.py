#Flags
practiceBlocks = False
practicing = False
testing = False

#Paths
paths = {'font': 'default', 'image': 'assets/img', 'asset': 'assets', 'db': 'data'}

#Graphics Settings
isCRT = False
if isCRT is True:
	dpi = 75
else:
	dpi = 96

#Stimulus Settings (Specify sizes in DoVA, positions as x,y distance from the center in DoVA)
dimensions = {
'strokeThickness': 0.5,
'boxSize': 3.0,
'fixSize': 2.0
}

locations = {
'center': [0.0, 0.0],
'top-left': [5.0, -5.0],
'top-right': [5.0, 5.0],
'bottom-left': [-5.0, -5.0],
'bottom-right': [-5.0, 5.0]
}

#Trial Settings
blocks = 1  #50
blockLogs = {'incorrect': 0, 'correct': 0, 'notarget': 0, 'timeout': 0, 'trials': 0}
blockLogTemplate = blockLogs.copy()
blockAccuracy = 0
blockCount = 0

trialCount = 0
trialsPerBlock = 20
trialsPerPracticeBlock = 'default'
trialStart = None

#Database
DBName = 'ExperimentName'
LoggedFields = {'RT': None, 'Cued': None, }

#Response Mappings
keyMaps = {'default':['SPACEBAR',32,1], '*':['*',-1,True]}

#Thesaurus
thesaurus = {'one': 1, 'single': 1, 'two': 2, 'double': 2, 'None': None, 'False': False, 'True': True, 'No': False}

