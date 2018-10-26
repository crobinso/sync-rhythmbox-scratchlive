
import atexit
import glob
import os
import shutil
import unittest

import tests

datadir = os.path.join(os.path.dirname(__file__), "data")
rhythmbox_xml = os.path.join(datadir, "rhythmdb.xml")
rhythmbox_scratch_input = os.path.join(datadir, "rhythmbox_sync.db")
rmfiles = []


def _cleanup():
    for base in rmfiles:
        for f in glob.glob(base + "*"):
            try:
                os.unlink(f)
            except Exception:
                continue


atexit.register(_cleanup)


class Cli(unittest.TestCase):
    """
    Tests for running scratchlivedb-tool
    """
    maxDiff = None

    def testSyncRhythmbox(self):
        """
        Basic test for rhythmbox sync, make sure we see expected output
        """
        tmpfile = rhythmbox_scratch_input + ".tmp"
        shutil.copy(rhythmbox_scratch_input, tmpfile)
        rmfiles.append(tmpfile)

        cmd = ("sync-rhythmbox-scratchlive --in-place %s %s" %
               (rhythmbox_xml, tmpfile))
        out = tests.clicomm(cmd)

        assert "Changing timeadded:  Armored_Core/Armored_" in out
        assert "Removing from DB:    Orb/Orb_-_Adv" in out
        assert "Adding to DB:        Orbital/Orbital_-_In_S" in out
        assert "Adding to DB:        Daft_Punk/Daft_Punk_-_Tr" in out
        assert "Adding to DB:        Advantage/Advantage_-_Th" in out

        # Make sure running twice doesn't make any changes
        out = tests.clicomm(cmd)
        assert "Parsing rhythmbox DB\n\nTotal removed:" in out
