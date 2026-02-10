from klibs.KLStructure import FactorSet, Block

""" ##### FactorSet Tutorial #####

This file specifies the different trial factors and their levels for the experiment.

For example, a spatial cueing task (where participants are cued to respond to targets
on the left or right side of the screen) might have the following factors that change
from trial to trial:

  1) The validity of the spatial cue (same or different location from target)
  2) The location of the spatial cue (left or right of screen)
  3) The onset delay between the cue and target (200, 400, or 800 ms)
  4) The presence of an auditory alerting tone (present or absent)

In addition to the above, let's say you want cues to be valid 66% of the time. To 
specify this sort of factor structure, you can do something like this:

exp_factors = FactorSet({
    'cue_validity': ['valid', 'valid', 'invalid'],
    'cue_location': ['left', 'right'],
    'target_onset': [200, 400, 800],
    'alerting_tone': [True, False],
})

When the experiment is launched, the FactorSet will be loaded by the klibs runtime and
used to generate trials based on the full set of unique combinations of factors.

Specifically, the klibs runtime creates an attribute corresponding to each factor in the
set within the Experiment (e.g. `self.cue_validity`, `self.target_onset`), and updates
their values with their generated per-trial values on each trial. During `self.trial`
and `self.trial_prep` you can use these values to write dynamic code based on the
factors defined in your FactorSet:

    self.trial_prep(self):
        # Determine cue and target locations for the trial
        valid_cue = self.cue_validity == "valid"
        if self.cue_location == "left":
            self.cue_loc = self.left_loc
            self.target_loc = self.left_loc if valid_cue else self.right_loc
        else:
            self.cue_loc = self.right_loc
            self.target_loc = self.right_loc if valid_cue else self.left_loc

If a level of a factor is repeated multiple times (e.g. 3 valid cues per invalid cue),
you can also note this using a `(level, count)` tuple as shorthand, e.g. `('valid', 3)`.

"""

exp_factors = FactorSet({
    # Insert trial factors here
})


""" ##### Structure Tutorial #####

In addition to specifying trial factors and their levels, you can also use this file to
specify a custom block structure for the experiment.

By default, klibs will generate blocks of trials using the factors defined above and
the number of blocks (and trials per block) specified in the project's params.py file.
For experiments that require more complex block structures, such as blocks with
different lengths or different factors, you can define your own sequences of blocks
using Block objects:

structure = [
    Block(exp_factors, trials=24, practice=True),
    Block(exp_factors, trials=96),
    Block(exp_factors, trials=96),
]

This would specify a simple 3-block structure: a 24 trial practice block followed by
two 96 trial test blocks.

### Block Factors ###

In many experiments, you might want to have different block types with different factor
levels (e.g. blocks with different difficulties, stimulus types, or task demands). As
such, the Block class makes it easy to use custom factor sets for different blocks.

For example, to extend the FactorSet example above and add blocks of trials that have
50% cue validity, you could do the following:

endo_factors = exp_factors
exo_factors = exp_factors.override({
    'cue_validity' : ['valid', 'invalid']
})

exo = Block(exo_factors, label='exo')
endo = Block(endo_factors, label='endo')

structure = [
    exo, endo, exo, endo
]

### Block Labels & Practice Blocks ###

If you specify a label for a block, the value of this label can be accessed from within
the experiment runtime through the attribute `self.block_label`. For example, at the
start of each block you can show different instructions depending on the block label:

    self.block(self):
        # Show instructions based on block type
        if self.block_label == "endo":
            self.show_endo_instructions()
        elif self.block_label == "exo":
            self.show_exo_instructions()

Similarly, setting `practice` to True for a block will flag it as a practice block,
meaning that `P.practicing` will be set to True while within the block.

"""

structure = []
