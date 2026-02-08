__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import random
from collections import OrderedDict
from copy import deepcopy
        
from klibs import P
from klibs.KLInternal import load_source
from klibs.KLStructure import FactorSet, Block


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


def _load_structure(path):
    # Imports a custom task structure from a file, returning an empty list if
    # a structure is not specified.

    ind_vars = load_source(path)
    if not 'structure' in ind_vars.keys():
        return []

    structure = ind_vars['structure']
    if structure:
        try:
            structure = list(structure)
        except Exception:
            e = "If specified, task structure must be a list of Blocks."
            raise TypeError(e)

    return structure


def _parse_structure(structure, exp_factors):
    # Parses/validates a custom task structure and returns a list of TrialSets

    count = 0
    blocks = []
    for block in structure:

        if not isinstance(block, Block):
            raise TypeError("Task structure must be made of Blocks")

        # Ensure all blocks have same factor levels
        count += 1
        extra = set(block.factors) - set(exp_factors)
        missing = set(exp_factors) - set(block.factors)
        if len(extra):
            e = "Extra factors" if len(extra) > 1 else "Extra factor"
            e += " in block {0} not present in exp_factors: {1}"
            raise RuntimeError(e.format(count, str(list(extra))))
        if len(missing):
            e = "Missing the following factors in block {0}: {1}"
            raise RuntimeError(e.format(count, str(list(missing))))

        # Skip practice blocks if disabled
        if block.practice and not P.run_practice_blocks:
            continue

        # Generate trials and add block to block sequence
        trials = block.get_trials()
        b = TrialSet(trials, block.practice, block.label)
        blocks.append(b)

    return blocks


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


def _block_to_str(block, num):
    # Generates a string describing the structure and factor levels for each
    # trial in a given block

    # Generate a block header
    info = "{0} trials".format(len(block))
    info += ", '{0}'".format(block.label) if block.label else ""
    info += ", Practice" if block.practice else ""
    block_info = "== Block {0} ({1}) ==".format(num, info)
    out = ["=" * len(block_info), block_info, "=" * len(block_info)]

    # Get max character length for each factor level for sake of alignment
    col_pad = {'trial': max(len(str(len(block))), len('trial'))}
    factors = list(block.trials[0].keys())
    for f in factors:
        if not f in col_pad.keys():
            col_pad[f] = len(f)
        for row in block.trials:
            if len(str(row[f])) > col_pad[f]:
                col_pad[f] = len(str(row[f]))

    if len(factors):
        cols = ['trial'] + factors

        # Generate a header for the different factors
        out.append("")
        out.append(" ".join([col.ljust(col_pad[col]) for col in cols]))
        out.append(" ".join(["-" * col_pad[col] for col in cols]))

        # Write the factor levels for each trial in the block
        t = 1
        for trial in block.trials:
            row = str(t).ljust(col_pad['trial']) + " "
            row += " ".join([str(trial[f]).ljust(col_pad[f]) for f in factors])
            out.append(row)
            t += 1

    out.append("")
    return "\n".join(out)


def _structure_to_str(blocks, factors):
    # Converts the block structure, experiment factors, and trial sequence for
    # each block into a human-readable string

    # Write out the block structure
    out = []
    out.append("")
    out.append("Blocks:")
    for i in range(len(blocks)):
        b = str(blocks[i]).replace("TrialSet", "")
        out.append(" - Block {0}: ".format(i+1) + b)
    out.append("")
    
    # Write out the factor list
    if len(factors.items()):
        out.append("Factors:")
        for name, values in factors.items():
            out.append(" - {0}: {1}".format(name, values))
    else:
        out.append("Factors: None")

    # Write out the trials (and factors) for each block
    out.append("\n")
    block_num = 1
    for b in blocks:
        out.append("")
        out.append(_block_to_str(b, block_num))
        block_num += 1

    return "\n".join(out)



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
    """Generates blocks of trials using a given set of categorical factors.

    For internal use.

    Args:
        factors (dict): A dict containing the factor names and factor levels
            to use for generating trials.

    """
    def __init__(self, factors):
        # Create alphabetically-sorted ordered dict from factors
        self.exp_factors = OrderedDict(sorted(factors.items(), key=lambda t: t[0]))
        self.blocks = None


    def trial_generator(self, factors, block_count, trial_count):
        """Method that actually generates blocks of trials.

        """
        # NOTE: Factored into a separate function for easier unit testing
        return _generate_blocks(factors, block_count, trial_count)


    def generate(self, num_blocks=None, trials_per_block=None):
        """Generates an initial set of blocks.

        """
        # If block/trials-per-block counts aren't specified, use values from params.py
        if num_blocks is None:
            num_blocks = 1 if P.blocks_per_experiment <= 0 else P.blocks_per_experiment
        if trials_per_block is None:
            trials_per_block = P.trials_per_block
        
        blocks = self.trial_generator(self.exp_factors, num_blocks, trials_per_block)
        self.blocks = [TrialSet(b) for b in blocks]


    def insert_block(self, block_num, trials=0, practice=False, factor_mask=None):
        """Inserts a new block of trials into the block sequence.

        Args:
            block_num (int): The block number for the inserted block.
            trials (int, optional): The trial count for the block. If not specified, a
                block containing a full set of factor combinations will be inserted.
            practice (bool, optional): Whether to flag the block as a practice block.
                Defaults to False.
            factor_mask (dict, optional): A dict containing overrides for the levels of
                one or more of the factors.

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

        block = self.trial_generator(factors, 1, trials)[0]
        # there is no "zero" block from the UI/UX perspective, so adjust insertion accordingly
        self.blocks.insert(block_num - 1, TrialSet(block, practice=practice))


    def export_trials(self):
        """Exports the current block sequence.

        """
        if not self.blocks:
            self.generate()

        return self.blocks


    def dump(self):
        # Compat: Can remove once taken out of TraceLab
        outpath = os.path.join(P.local_dir, "TrialFactory_dump.txt")
        with open(outpath, "w") as log_f:
            log_f.write(_structure_to_str(self.blocks, self.exp_factors))
