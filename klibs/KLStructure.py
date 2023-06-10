import itertools
from copy import deepcopy
from collections import OrderedDict

from klibs.KLInternal import iterable


class FactorSet(object):
    """A class representing the full set of factors for an experiment.

    For example, a simple attention cueing paradigm might have 3 factors:
    target location (left or right), cue validity (valid, invalid, or neutral),
    and stimulus onset asynchrony (SOA, i.e. the time delay between the onset of
    the cue and target stimuli, in this case 200, 400, or 800 ms). Specifying
    this structure in a FactorSet would look something like this::

        factors = FactorSet({
            'target_loc': ['left', 'right'],
            'cue_validity': ['valid', 'invalid', 'neutral'],
            'soa': [200, 400, 800],
        })

    This creates a set with 18 unique factor combinations (2 x 3 x 3 = 18) that
    can be then used within KLibs.

    If a level of a factor is repeated multiple times, you can specify this by
    either repeating the level (e.g. ``[True, True, False]``) or by using a
    ``(level, count)`` tuple as shorthand (e.g. ``[(True, 2), False]``). Apart
    from those in this specific format, tuples are not supported as valid
    factor levels.

    Args:
        factors (dict): A dictionary in the format ``{'factor': values}``,
            specifying all possible levels of each factor in the set.

    """
    def __init__(self, factors={}):
        self._factors = OrderedDict()
        for factor, levels in factors.items():
            self._factors[factor] = self._parse_levels(levels)

    def _validate_tuple(self, x):
        # Ensures a tuple is in the correct 'repeating level' shorthand
        if not len(x) == 2 or not isinstance(x[1], int):
            e = ("Tuples are not supported as factors except in (level, count) "
                 "form to specify a repeating level.")
            raise RuntimeError(e)

    def _parse_levels(self, levels):
        # If level isn't iterable, return as a single-item list
        if not iterable(levels):
            return [levels]
        # Unpack any 'repeated level' tuples in the list
        out = []
        for level in levels:
            if isinstance(level, tuple):
                self._validate_tuple(level)
                value, count = level
                out += [value] * count
            else:
                out.append(level)
        return out
        
    def _get_combinations(self):
        # Generates a list of all unique factor combinations in the set
        factor_names = list(self._factors.keys())
        factor_levels = [self._factors[f] for f in factor_names]
        factor_set = []
        for combination in itertools.product(*factor_levels):
            trial_dict = dict(zip(factor_names, combination))
            factor_set.append(trial_dict)
        return factor_set

    def override(self, factor_mask):
        """Creates a new copy of the factor set with a given set of overrides.

        For example, if you wanted to define factor sets for a study where some
        blocks have 50% cue validity and others have 66% cue validity, you could
        do the following::

            factors_50 =  FactorSet({
                'target_loc': ['left', 'right'],
                'cue_validity': ['valid', 'invalid'],
                'soa': [200, 400, 800],
            })

            factors_66 = factors_50.override({
                'cue_validity': ['valid', 'valid', 'invalid']
            })

        Note that all overrides must correspond to factors that currently exist
        within the set: this method only allows for modifying the levels of
        existing factors and does not allow for adding new factors.

        Args:
            factor_mask (dict): A dictionary in the form ``{'factor': values}``
                specifying which factors to override and the new values with
                which to override the existing factor levels.

        Returns:
            :obj:`FactorSet`: A new factor set with the given overrides applied.

        Raises:
            ValueError: If any factor in the override mask does not match the
                name of an existing factor in the set.
        
        """
        err = "Factor '{0}' does not exist within the set."
        new = deepcopy(self._factors)
        for factor in factor_mask.keys():
            if factor in self.names:
                new_levels = factor_mask[factor]
                new[factor] = new_levels
            else:
                raise ValueError(err.format(factor))
        return FactorSet(new)
        
    @property
    def names(self):
        """list: The names of all factors within the set."""
        return list(self._factors.keys())

    @property
    def set_length(self):
        """int: The number of trials required for the full factor set."""
        return len(self._get_combinations())
