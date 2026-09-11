# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import random
from abc import abstractmethod
from traceback import print_tb, print_stack

from klibs import P
from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import TrialException, TerminateBlock
from klibs.KLInternal import full_trace, iterable, load_source
from klibs.KLInternal import colored_stdout as cso


class Experiment(EnvAgent):
    
    window = None
    paused = False

    def __init__(self):
        from klibs.KLEventInterface import EventManager
        from klibs.KLAudio import AudioManager
        from klibs.KLResponseCollectors import ResponseCollector
        from klibs.KLTrialFactory import TrialFactory

        super(Experiment, self).__init__()

        self.incomplete = True # flag for keeping track of session completeness
        self.blocks = None # blocks of trials for the experiment
        self.tracker_dot = None # overlay of eye tracker gaze location in devmode
        self.block_label = None # runtime attribute containing label of current block

        self.audio = AudioManager() # initialize audio management for the experiment
        self.rc = ResponseCollector() # add default response collector
        self.database = self.db # use database from env
        self._evm = EventManager()

        self._exp_factors, self._exp_structure = self._get_exp_structure()
        self.trial_factory = TrialFactory(self._exp_factors)


    def _get_exp_structure(self):
        # Reads in the trial factors and block structure (if any) for the study
        from klibs.KLTrialFactory import _load_factors, _load_structure

        # Load and parse _intependent_variables.py
        idvars = load_source(P.ind_vars_file_path)
        factors = _load_factors(idvars)
        structure = _load_structure(idvars)

        # Load and apply any local overrides
        if os.path.exists(P.ind_vars_file_local_path):
            if not P.dm_ignore_local_overrides:
                # Override values for individual factor levels
                local = load_source(P.ind_vars_file_local_path)
                local_factors = _load_factors(local)
                factors.update(local_factors)
                # Use local structure if specified
                local_structure = _load_structure(local)
                if structure and local_structure:
                    structure = local_structure
            
        return factors, structure


    def __execute_experiment__(self, *args, **kwargs):
        """For internal use, actually runs the blocks/trials of the experiment in sequence.

        """
        if not P.demographics_collected:
            e = "Demographics must be collected prior to the start of the first block."
            raise RuntimeError(e)

        if self.blocks == None:
            self.blocks = self.trial_factory.export_trials()

        P.blocks_per_experiment = len(self.blocks)
        P.block_number = 0
        P.trial_id = 0
        for block in self.blocks:
            P.recycle_count = 0
            P.block_number += 1
            P.trials_per_block = len(block)
            P.practicing = block.practice
            self.block_label = block.label
            self.block()
            P.trial_number = 1
            remaining = list(block.trials)
            if P.max_trials_per_block != False:
                remaining = remaining[:P.max_trials_per_block]
            while len(remaining):
                trial = remaining.pop(0)
                try:
                    P.trial_id += 1 # Increments regardless of recycling
                    self.__trial__(trial)
                    P.trial_number += 1
                except TrialException:
                    remaining = self._recycle_trial(remaining, trial)
                    P.recycle_count += 1
                except TerminateBlock:
                    remaining = []
                self.rc.reset()
        self.clean_up()

        self.incomplete = False
        if 'session_info' in self.database.tables:
            where = {'session_number': P.session_number}
            self.database.update('session_info', {'complete': True}, where)


    def __trial__(self, trial):
        """
        Private method; manages a trial.
        """
        from klibs.KLEventQueue import flush
        from klibs.KLUserInterface import show_cursor, hide_cursor

        # At start of every trial, before setup_response_collector or trial_prep are run, retrieve
        # the values of the independent variables (factors) for that trial (as generated earlier by
        # TrialFactory) and set them as attributes of the experiment object.
        for iv, value in trial.items():
            setattr(self, iv, value)

        # Run trial prep methods
        self.setup_response_collector()
        self.trial_prep()
        flush()

        # Get everything ready to start the trial
        trylink = P.eye_tracking and not P.eye_tracker_available
        if P.development_mode and (P.dm_trial_show_mouse or trylink):
            show_cursor()
        if P.eye_tracking and not P.manual_eyelink_recording:
            self.el.start(P.trial_number)
        self.evm.start_clock()

        # Actually run the trial and log the data to the database
        exc = None
        try:
            P.in_trial = True
            self.__log_trial__(self.trial())
            P.in_trial = False
        except (TrialException, TerminateBlock) as e:
            exc = e

        # Clean up after the trial
        self.evm.stop_clock()
        if P.eye_tracking and not P.manual_eyelink_recording:
            self.el.stop()
        if P.development_mode and (P.dm_trial_show_mouse or trylink):
            hide_cursor()
        self.trial_clean_up()

        # Raise TerminateBlock or TrialException if encountered
        if exc:
            raise exc


    def __log_trial__(self, trial_data):
        """Internal method, logs trial data to database.

        """
        from klibs.KLDatabase import EntryTemplate

        trial_template = EntryTemplate('trials')
        trial_template.log(P.id_field_name, P.participant_id)
        for attr in trial_data:
            trial_template.log(attr, trial_data[attr])

        return self.database.insert(trial_template)


    def _recycle_trial(self, remaining, trial):
        """Internal method for recycling a trial within the current block.

        This method re-inserts a trial into the set of remaining trials at a
        random position, avoiding an immediate repeat of the trial unless it is
        the only trial remaining in the block.

        Recycling behaviour can be customized by overriding this method.

        Args:
            remaining (list): The remaining trials for the current block.
            trial (dict): The trial factors to recycle into the block.

        Returns:
            list: The new set of remaining trials.

        """
        # NOTE: Should this be part of public API or stay unofficial/internal?
        if len(remaining):
            # Re-insert the trial in a random position after the first element
            tmp = remaining.copy()
            new_idx = random.randrange(1, len(tmp)) if len(tmp) > 1 else 1
            tmp.insert(new_idx, trial)
            return tmp
        else:
            return [trial]


    ## Define abstract methods to be overridden in experiment.py ##

    @abstractmethod
    def setup(self):
        """The first part of the experiment that gets run. Locations, sizes, stimuli, and
        other experiment resources that stay the same throughout the experiment should be
        initialized and defined here.

        """
        pass

    @abstractmethod
    def block(self):
        """Run once at the start of every block. Block messages, block-level stimulus generation,
        and similar content should go here.

        """
        pass

    @abstractmethod
    def setup_response_collector(self):
        """Run immediately before trial_prep during each iteration of the trial loop. If using a
        :obj:`~klibs.KLResponseCollectors.ResponseCollector` that requires configuration at the
        start of each trial, that code should go here.
        
        """
        pass
    
    @abstractmethod
    def trial_prep(self):
        """Run immediately before the start of every trial. All trial preparation unrelated to
        response collection should go here.

        """
        pass

    @abstractmethod
    def trial(self):
        """The core of the experiment. All code related to the presentation of stimuli during a
        given trial, the collection and processing of responses, and the writing out of primary
        data should go here.

        The timing of events in the built-in :obj:`~klibs.KLEventManager.EventManager` instance
        (``self.evm``) are all relative to when this method is called.

        """
        pass

    @abstractmethod
    def trial_clean_up(self):
        """Run immediately after the end of every trial.

        """
        pass
    
    @abstractmethod
    def clean_up(self):
        """Run once at the end of the experiment, after all trials have been completed. Anything
        you want to happen at the very end of the session should go here.

        """
        pass
    

    def insert_practice_block(self, block_nums, trial_counts=None, factor_mask=None):
        """Adds a practice block to the experiment.

        This method adds an extra block of trials at a given position in the block
        sequence, optionally with a different trial count and/or different factor
        levels than the rest of the task. For example, to add a practice block with
        20 trials at the start of the task, you would add the following somewhere in
        the `setup()` block of your `experiment.py` file::

           self.insert_practice_block(1, 20)

        During practice blocks the klibs parameter `P.practicing` will be set to True,
        allowing easy conditional changes during practice blocks (e.g. showing
        additional feedback if practicing).

        You can also provide a factor mask to override one or more factor levels for
        the practice block. For example, if the task has a factor 'difficulty' with
        the levels 'easy' and 'hard' and you want to add separate practice blocks for
        each trial type, you can specify overrides for the factor levels like so::

           self.insert_practice_block(1, 32, factor_mask={'difficulty': ['easy']})
           self.insert_practice_block(2, 32, factor_mask={'difficulty': ['hard']})

        This function must be called during setup(), otherwise the block structure of
        the study will already be set and can no longer be changed.

        Args:
            block_nums (int): Position at which to insert the block.
            trial_counts (int, optional): The trial count for the practice block.
                Defaults to `P.trials_per_block`.
            factor_mask (:obj:`dict` of :obj:`list`, optional): Overrides for one or
                more factors in the task's `independent_variables.py` file.

        """
        # [Compat]: Messy API to allow multiple insertions at once, fix when possible.
        # Only TOJ_Motion uses multiple insertions. Multiple projects use 'trial_counts'
        # keyword, however.

        if self.blocks:
            if self._exp_structure:
                e = "in setup() when using a custom block structure."
            else:
                e = "after setup() is complete."
            raise RuntimeError("Cannot insert practice blocks " + e)

        if not trial_counts:
            trial_counts = P.trials_per_block

        if iterable(block_nums):
            # [Compat]: Only TOJ_Motion uses this and it's a bad idea, remove when fixed.
            for b in block_nums:
                self.insert_practice_block(b, trial_counts, factor_mask)
        else:
            self.trial_factory.insert_block(block_nums, trial_counts, True, factor_mask)

    
    def write_trials_txt(self, outpath=None):
        """Writes the current block/trial structure to a text file.

        This method is intended for verifying your blocks and trials are being
        generated and sequenced as expected during development. The factors for
        each trial within each block are written in a human-readable format::

            =========================
            == Block 1 (3 trials) ==
            =========================

            trial cue_validity soa target_loc
            ----- ------------ --- ----------
            1     valid        200 left
            2     invalid      800 right         
            3     neutral      800 left

        A summary of the block structure and a list of the experiment factors
        and their base levels is also included at the top of the file.

        Args:
            outpath (str, optional): The path at which to save the text file.
                Defaults to `ExpAssets/Local/[project_name]_trials.txt`.

        """
        from klibs.KLTrialFactory import _structure_to_str

        if not outpath:
            fname = "{0}_trials.txt".format(P.project_name)
            outpath = os.path.join(P.local_dir, fname)

        with open(outpath, "w") as out:
            blocks = self.blocks if self.blocks else self.trial_factory.blocks
            out.write(_structure_to_str(blocks, self.exp_factors))

    
    def before_flip(self):
        """A method called immediately before every refresh of the screen (i.e. every time
        :func:`~klibs.KLGraphics.flip` is called).
        
        By default, this is used for drawing the current gaze location to the screen when using an
        eye tracker (and ``P.show_gaze_dot`` is True), but can be overridden with a different
        function if desired.

        """
        from klibs.KLGraphics import blit

        if P.show_gaze_dot and self.el.recording:
            try:
                blit(self.tracker_dot, 5, self.el.gaze())
            except RuntimeError:
                pass


    def quit(self):
        """Safely exits the program, ensuring data has been saved and any connected EyeLink unit's
        recording is stopped. This, not Python's sys.exit(), should be used to exit an experiment.

        """
        import sdl2
        if P.verbose_mode:
            print_tb(print_stack(), 6)

        err = ''
        try:
            self.database.commit()
            self.database.close()
        except Exception:
            err += "<red>Error encountered closing database connection:</red>\n\n"
            err += full_trace()+"\n\n"
            err += "<red>Some data may not have been saved.</red>\n\n\n"

        if P.eye_tracking and P.eye_tracker_available:	
            try:
                self.el.shut_down(incomplete=self.incomplete)
            except Exception:
                err += "<red>Eye tracker encountered error during shutdown:</red>\n\n"
                err += full_trace()+"\n\n"
                err += "<red>You may need to manually stop the tracker from recording.</red>\n\n\n"

        if P.multi_user and P.version_dir:
            newpath = P.version_dir.replace(str(P.random_seed), str(P.participant_id))
            os.rename(P.version_dir, newpath)

        self.audio.shut_down()
        sdl2.ext.quit()

        if err:
            cso("\n\n" + err + "<red>*** Errors encountered during shutdown. ***</red>\n\n")
            os._exit(1)
        cso("\n\n<green>*** '{0}' successfully shut down. ***</green>\n\n".format(P.project_name))
        os._exit(1)


    def run(self, *args, **kwargs):
        """The method that gets run by 'klibs run' after the runtime environment is created. Runs
        the actual experiment.

        """
        from klibs.KLGraphics.KLDraw import Ellipse
        from klibs.KLTrialFactory import _parse_structure
    
        if P.eye_tracking:
            RED = (255, 0, 0)
            WHITE = (255, 255, 255)
            self.tracker_dot = Ellipse(8, stroke=[2, WHITE], fill=RED).render()
            if not P.manual_eyelink_setup:
                self.el.setup()
        
        # Generate blocks of trials (from either custom structure or trial factory)
        if self._exp_structure:
            self.blocks = _parse_structure(self._exp_structure, self.exp_factors)
        elif P.manual_trial_generation is False:
            self.trial_factory.generate()

        self.setup()
        try:
            self.__execute_experiment__(*args, **kwargs)
        except RuntimeError:
            print(full_trace())

        self.quit()


    def show_logo(self):
        from klibs.KLEventQueue import flush
        from klibs.KLUserInterface import any_key
        from klibs.KLGraphics import fill, blit, flip
        from klibs.KLGraphics import NumpySurface as NpS
        logo = NpS(P.logo_file_path)
        flush()
        for i in (1, 2):
            fill()
            blit(logo, 5, P.screen_c)
            flip()
        any_key()


    @property
    def exp_factors(self):
        """dict: The names and levels of all categorical factors in the study.

        This attribute is read-only, meaning that any changes to this attribute's
        keys or values will have no effect on the experiment runtime.

        """
        return self._exp_factors.copy()


    @property
    def participant_info(self):
        """dict: The demographics values for the current participant.

        This property allows easy access to the current participant's self-reported
        demographics attributes (e.g. handedness) for cases where these attributes
        affect the experiment runtime (e.g. different instructions and/or controls
        for left-handed participants)::

           handedness = self.participant_info['handedness']
           self.button_loc = b_left_loc if handedness == "l" else b_right_loc
               
        The keys of this dict correspond to the columns in the 'participants' table
        of the task's database.

        This attribute is read-only, meaning that any changes to this attribute's
        keys or values will have no effect on the experiment runtime.

        """
        if not P.demographics_collected:
            e = "Demographics accessed prior to demographics collection."
            raise RuntimeError(e)
        
        colnames = self.database.get_columns('participants')
        values = self.database.select('participants', where={'id': P.p_id})[0]
        out = {}
        for i in range(len(colnames)):
            if not colnames[i] == 'id':
                out[colnames[i]] = values[i]
        return out


    @property
    def evm(self):
        """:obj:`~klibs.KLEventInterface.EventManager`: The trial event sequencer for
        the experiment.

        Is automatically started just prior to running :meth:`trial`, and automatically
        reset when each trial ends.

        """
        return self._evm
