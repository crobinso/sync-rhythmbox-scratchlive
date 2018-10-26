import argparse
import datetime
import logging
import os
import shutil
import sys
from xml.etree import ElementTree

import scratchlivedb
from scratchlivedb.scratchdb import log

log = logging.getLogger("scratchlivedb")
log.setLevel(logging.DEBUG)


###################
# Utility methods #
###################

def fail(msg):
    print >> sys.stderr, "ERROR: %s" % msg
    sys.exit(1)


######################
# Main syncing logic #
######################

class SyncRhythmbox(object):
    """
    Pull music info from rhythmbox's DB.
    """
    def __init__(self, source):
        self.source = source

        if not self.source:
            self.source = os.path.expanduser(
                        "~/.local/share/rhythmbox/rhythmdb.xml")
        self._db = self._parse_rhythmdb(self.source)


    ###############
    # Private API #
    ###############

    def _find_shared_root(self, paths):
        """
        Given a list of paths, find the shared root path
        """
        ret = paths[0]

        for key in paths:
            tmpbase = ret
            logged = False

            while not key.startswith(tmpbase):
                if not logged:
                    log.debug("key=%s doesn't start with base=%s, "
                              "shrinking it", key, tmpbase)
                    logged = True
                tmpbase = tmpbase[:-1]

            ret = tmpbase
        return ret

    def _parse_rhythmdb(self, path):
        """
        Parse the rhythmbox db, return a dictionary of mapping
        filename->timestamp
        """
        if not os.path.exists(path):
            raise RuntimeError("Didn't find rhythmdb at %s" % path)

        db = {}
        root = ElementTree.parse(path).getroot()

        # First pass, just full out raw path and timestamp
        for child in root:
            if child.tag != "entry" or child.attrib.get("type") != "song":
                continue

            prefix = "file:///"
            location = child.find("location").text
            if not location.startswith(prefix):
                raise RuntimeError("rhythmbox location didn't start with "
                                   "expected file:/// : '%s'" % location)

            if (child.find("hidden") is not None and
                child.find("hidden").text == "1"):
                continue

            first_seen = int(child.find("first-seen").text)
            db[location[(len(prefix) - 1):]] = first_seen

        source_base_dir = self._find_shared_root(db.keys()[:])
        log.debug("Found source_base_dir=%s", source_base_dir)

        # Third pass, strip source_base_dir from paths
        for key in db.keys():
            db[key[len(source_base_dir):]] = db.pop(key)

        return db


    ##############
    # Public API #
    ##############

    def sync(self, db, require_base=None):
        dbroot = self._find_shared_root([e.filebase for e in db.entries])
        log.debug("Found scratchlivedb base=%s", dbroot)
        if require_base is not None and dbroot != require_base:
            raise RuntimeError("Required base '%s' doesn't match detected "
                               "base '%s'" % (require_base, dbroot))

        def p(desc, key):
            print "%-20s %s" % (desc + ":", key)

        def round_to_day(ctime):
            """
            Round ctime value down to midnight, so that slight variations
            in times are all set to the same value, which helps us
            sort in scratch live
            """
            fmt = "%Y-%m-%d"
            strtime = datetime.datetime.fromtimestamp(int(ctime)).strftime(fmt)
            return int(datetime.datetime.strptime(strtime, fmt).strftime("%s"))

        rmcount = 0
        changecount = 0
        addcount = 0

        for entry in db.entries[:]:
            key = entry.filebase[len(dbroot):]
            if key not in self._db:
                p("Removing from DB", key)
                rmcount += 1
                db.entries.remove(entry)
                continue

            newtime = round_to_day(self._db.pop(key))
            if newtime != entry.inttimeadded:
                desc = "%s %s->%s" % (key,
                        datetime.datetime.fromtimestamp(entry.inttimeadded),
                        datetime.datetime.fromtimestamp(newtime))
                changecount += 1
                p("Changing timeadded", desc)

                entry.inttimeadded = newtime

        for key, timestamp in self._db.items():
            addcount += 1
            p("Adding to DB", key)
            newentry = db.make_entry(dbroot + key)
            newentry.inttimeadded = round_to_day(timestamp)
            db.entries.append(newentry)

        print
        print "Total removed: %d" % rmcount
        print "Total added:   %d" % addcount
        print "Total changed: %d" % changecount


###################
# main() handling #
###################

def setup_logging(debug):
    handler = logging.StreamHandler(sys.stderr)
    if debug:
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(levelname)-6s (%(module)s:%(lineno)d): %(message)s")
    else:
        handler.setLevel(logging.WARN)
        formatter = logging.Formatter("%(levelname)-6s %(message)s")

    handler.setFormatter(formatter)
    log.addHandler(handler)

    log.debug("Launched with command line: %s", " ".join(sys.argv))


def parse_options():
    desc = ("Sync DB with rhythmbox library."
            "Only scratch DB is altered. Currently this only "
            "removes missing files and syncs timeadded value.")
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("rhythmdb",
            help="Path to rhythmbox db xml file")
    parser.add_argument("scratchlivedbfile",
            help="Path to scratchlive db file ex. /path/to/database V2")
    parser.add_argument("--debug", action="store_true",
            help="Print debug output to stderr")

    parser.add_argument("--in-place", action="store_true",
            help="Overwrite database in place, making a backup first.")
    parser.add_argument("--require-base",
            help="Require this string to be the base directory "
                 "of every entry in the Scratch Live DB. Prevents "
                 "an errant file on say the desktop that's added to "
                 "the DB from messing up our sync logic.")
    parser.add_argument("--outfile", default="./out.db",
            help="New DB file to write (default=%default)")
    parser.add_argument("--dry-run", action="store_true",
            help="Don't save any changes")

    return parser.parse_args()


def main():
    options = parse_options()
    setup_logging(options.debug)
    dbfile = options.scratchlivedbfile

    print "Parsing database: %s" % dbfile
    db = scratchlivedb.ScratchDatabase(dbfile)

    print "Parsing rhythmbox DB"
    sync = SyncRhythmbox(options.rhythmdb)
    sync.sync(db, require_base=options.require_base)

    outfile = options.outfile
    if options.in_place:
        outfile = dbfile

    drystr = options.dry_run and " (dry)" or ""
    if os.path.exists(outfile):
        date = str(datetime.datetime.today()).replace(" ", "_")
        bak = outfile + "-%s.bak" % date
        bak = bak.replace(" ", "_").replace(":", "_")

        if os.path.exists(bak):
            fail("Generated backup path already exists: %s" % bak)

        print "Backing up to %s%s" % (bak, drystr)
        if not options.dry_run:
            shutil.copyfile(dbfile, bak)

    print "Writing %s%s" % (outfile, drystr)
    if not options.dry_run:
        file(outfile, "w").write(db.get_final_content())

    return 0
