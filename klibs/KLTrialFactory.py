__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import random
from collections import OrderedDict
from copy import deepcopy
        
from klibs import P
from klibs.KLInternal import load_source
from klibs.KLStructure import FactorSet


def _load_factors(path):
    # Imports either a FactorSet or IndependentVariableSet from a file and
    # coerces it to a dict of trial factors.

    # Try loading an IndependentVariableSet first, if one exists
    ind_vars = load_source(path)
    set_name = "{0}_ind_vars".format(P.project_name)
    if set_name in ind_vars.keys():
        factors = ind_vars[set_name].to_dict()

    # Otherwise, try loading a FactorSet
    elif "exp_factors" in ind_vars.keys():
        factors = ind_vars["exp_factors"]._factors

    else:
        err = "Unable to find a valid factor set in '{0}'."
        raise RuntimeError(err.format(path))

    return factors


def _generate_blocks(factors, block_count, trial_count):
    # Generates a list of blocks (which are lists of trials, which are dicts of
    # trial factors) based on a given factor set, trial count, & block count.

    # Convert factor dict into a FactorSet
    factors = FactorSet(factors)

    # Determine the correct trial count
    if trial_count <= 0:
        trial_count = factors.set_length

    # Generate a full set of shuffled blocks for the experiment
    blocks = []
    while len(blocks) < block_count:
        # Generate the trials for each block
        trials = []
        while len(trials) < trial_count:
            new = factors._get_combinations()
            remaining = trial_count - len(trials)
            random.shuffle(new)
            if remaining < len(new):
                new = new[:remaining]
            trials += new

        blocks.append(trials)

    return blocks



class TrialSet(object):
    """Class for representing blocks of trials.

    TrialSet objects are how klibs represents blocks of trials internally, and
    can be used to manually generate custom sequences of blocks/trials during
    the `self.setup()` phase of the Experiment runtime.

    The full set of blocks of trials for an experiment is stored as a list of
    TrialSets in the experiment attribute `self.blocks`. By default these blocks
    and trials are generated for you using the defined factors and specified
    block/trial counts in the project's configuration files, but you can use
    your own set of custom blocks by replacing the block list with your own::

        # Define a sequence of 3 trials
        trials = [{'image': 'a'}, {'image': 'b'}, {'image': 'c'}]

        # Set block sequence for task as 2 identical blocks of trials
        self.blocks = [
            TrialSet(trials, practice=True), # Flag block 1 as practice
            TrialSet(trials),
        ]

    If a block is provided with a label, the value of the label can be accessed
    during the block through the Experiment attribute `self.block_label`. This
    can be used to change things like stimuli or instructions conditionally
    in your code based on the block label (e.g. different cues for 'endo' and
    'exo' blocks).

    Note that custom block sequences can only be set during the `self.setup()`
    phase of the task.

    Args:
        trials (List): A list of dicts containing trial factors, with each dict
            representing a trial in the block.
        practice (bool, optional): Whether the block is a practice block. 
            Defaults to False.
        label (str, optional): A label optionally specifying the block type for
            experiments with multiple types of block. Defaults to None.

    """
    def __init__(self, trials, practice=False, label=None):
        self._trials = trials.copy()
        self.practice = practice
        self.label = label

    def __len__(self):
        return len(self._trials)

    def __str__(self):
        # Custom print method for better readability
        s = "{0} trials".format(len(self._trials))
        s += ", '{0}'".format(self.label) if self.label else ""
        s += ", Practice" if self.practice else ""
        return "TrialSet(" + s + ")"

    @property
    def trials(self):
        """List: The list of trials contained within the block."""
        return self._trials.copy()

# Alias for backwards compatibility
TrialIterator = TrialSet



class TrialFactory(object):

    def __init__(self):

        self.blocks = None
        self.trial_generator = self.__generate_trials

        # Load experiment factors from the project's _independent_variables.py file(s)
        factors = _load_factors(P.ind_vars_file_path)
        if os.path.exists(P.ind_vars_file_local_path):
            if not P.dm_ignore_local_overrides:
                local_factors = _load_factors(P.ind_vars_file_local_path)
                factors.update(local_factors)
        
        # Create alphabetically-sorted ordered dict from factors
        self.exp_factors = OrderedDict(sorted(factors.items(), key=lambda t: t[0]))


    def __generate_trials(self, factors, block_count, trial_count):
        # NOTE: Factored into a separate function for easier unit testing
        return _generate_blocks(factors, block_count, trial_count)


    def generate(self, exp_factors=None, block_count=None, trial_count=None):

        # If block/trials-per-block counts aren't specified, use values from params.py
        if block_count is None:
            block_count = 1 if not P.blocks_per_experiment > 0 else P.blocks_per_experiment
        if trial_count is None:
            trial_count = P.trials_per_block
        
        exp_factors = self.exp_factors if exp_factors == None else exp_factors
        blocks = self.trial_generator(exp_factors, block_count, trial_count)
        self.blocks = [TrialSet(b) for b in blocks]


    def export_trials(self):
        if not self.blocks:
            raise RuntimeError("Trials must be generated before they can be exported.")
        return self.blocks


    def insert_block(self, block_num, practice=False, trial_count=0, factor_mask=None):
        """

        :param block_num:
        :param practice:
        :param trial_count:
        :param factor_mask:
        """
        if factor_mask:
            if not isinstance(factor_mask, dict):
                raise TypeError("Factor overrides must be in the form of a dictionary.")
            
            factors = deepcopy(self.exp_factors) # copy factors to new list
            for name in factor_mask.keys():
                if name in factors.keys():
                    new_values = factor_mask[name]
                    if hasattr(new_values, '__iter__') == False:
                        new_values = [new_values] # if not iterable, put in list
                    factors[name] = new_values
                else:
                    e = "'{0}' is not the name of an active factor".format(name)
                    raise ValueError(e)
        else:
            # If no factor mask, generate trials randomly based on self.exp_factors
            factors = self.exp_factors

        # Don't insert practice blocks if practice blocks disabled
        if P.run_practice_blocks == False:
            return

        block = self.trial_generator(factors, 1, trial_count)[0]
        # there is no "zero" block from the UI/UX perspective, so adjust insertion accordingly
        self.blocks.insert(block_num - 1, TrialSet(block, practice=practice))
        P.blocks_per_experiment += 1


    def dump(self):
        # TODO: Needs a rewrite
        with open(os.path.join(P.local_dir, "TrialFactory_dump.txt"), "w") as log_f:
            log_f.write("Blocks: {0}, ".format(P.blocks_per_experiment))
            log_f.write("Trials: {0}\n\n".format(P.trials_per_block))
            log_f.write("*****************************************\n")
            log_f.write("*                Factors                *\n")
            log_f.write("*****************************************\n\n")
            for name, values in self.exp_factors.items():
                log_f.write("{0}: {1}\n".format(name, values))
            log_f.write("\n\n\n")
            log_f.write("*****************************************\n")
            log_f.write("*                Trials                 *\n")
            log_f.write("*****************************************\n\n")
            block_num = 1
            for b in self.blocks:
                log_f.write("Block {0}\n".format(block_num))
                trial_num = 1
                for t in b.trials:
                    log_f.write("\tTrial {0}: {1} \n".format(trial_num, t))
                    trial_num += 1
                block_num += 1
                log_f.write("\n")
