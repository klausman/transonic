#!/usr/bin/python3 -tt
"""Transonic, a massively parallel host pinger and result displayer"""
# Copyright (C) 2011 Tobias Klausmann

import argparse
import subprocess
import os
import sys
import time

from collections import namedtuple
from functools import partial
from multiprocessing import Pool

VERSION = "0.1"

# We hardcode these values because using the curses module is _way_ too brittle
# across assorted machines with somewhat functional terminfo databases. Not to
# mention that Python's curses API/wrapper is dreadful.
RED = '\x1b[38;5;1m'
NORMAL = '\x1b[m\x1b(B'
YELLOW = '\x1b[38;5;3m'
REVERSE = '\x1b[7m'

FORMATTERS = {}
TERSE = False

# NT: packets sent, packets received, loss percentage, total time passed
__Pingstats__ = namedtuple('__Pingstats__', "txcount rxcount lossprc totaltm")
# NT: minimum, average and maximum RTT, standard deviation
__RTTstats__ = namedtuple('__RTTstats__', "rmin ravg rmax rmdev")


class Pingresult:
    """Encapsulate one ping result, including RTT et al"""
    def __init__(self, hostname="UNKNOWN", pstats=None, rtt=None, retval=-1):
        self.hostname = hostname
        self.retval = retval
        if pstats:
            self.pstats = pstats
        else:
            self.pstats = __Pingstats__("?", "?", "?", "?")
        if rtt:
            self.rtt = rtt
        else:
            self.rtt = __RTTstats__("?", "?", "?", "?")

    def __str__(self):
        return ("%s S%s/R%s, maMD: %s/%s/%s/%s" %
            (self.hostname, self.pstats.txcount, self.pstats.rxcount,
             self.rtt.rmin, self.rtt.ravg, self.rtt.rmax, self.rtt.rmdev))


def eprint(fmt, *args):
    """
    Print fmt%args to stderr and add newline

    Note that this function looks at the global setting TERSE. Therefore
    it must not be used from the result formatters.

    """
    if not TERSE:
        sys.stderr.write(fmt % args)
        sys.stderr.write("\n")


def print_version():
    """Print version information and GPL minibanner"""
    print("%s %s" % (sys.argv[0].split(os.sep)[-1], VERSION))
    print("Licensed under the GPL. See COPYING for details")


def pinger(host, count):
    """
    Ping host count times and return Pingresult
    """
    #print("Ping job with PID %i for host %s starting" % (os.getpid(), host))
    rtts = None
    pstat = None
    cmd = "ping -c %i -q '%s'" % (count, host)
    (retval, output) = subprocess.getstatusoutput(cmd)

    for line in output.split("\n"):
        #print(line)
        if line[2:2+len("packets transmitted")] == "packets transmitted":
            stats = line.split()
            if "errors," in stats:
                pstat = __Pingstats__(int(stats[0]), int(stats[3]),
                                      int(stats[7][:-1]), int(stats[11][:-2]))
            else:
                pstat = __Pingstats__(int(stats[0]), int(stats[3]),
                                      int(stats[5][:-1]), int(stats[9][:-2]))
            continue

        if line.startswith("rtt min/avg/max/mdev"):
            rtts = line.split(None, 4)[3]
            r_min, r_avg, r_max, r_mdev = rtts.split("/")
            rtts = __RTTstats__(r_min, r_avg, r_max, r_mdev)
            continue
    res =  Pingresult(host, pstat, rtts, retval)
    #print(res)
    return res


def frl_list(resultlist, _):
    """Format the resultlist as a simple list, one host per line"""
    return "\n".join(str(x) for x in resultlist)
FORMATTERS["list"] = frl_list

def frl_cell(resultlist, replies):
    """
    Format the resultlist as "cells"

    The output format is:
     foo bar baz

    where hosts that do not meet the criteria are highlighted using a different
    color
    """
    counts = [0, 0]
    res = []
    for pres in resultlist:
        if pres.pstats.rxcount == "?" or replies > pres.pstats.rxcount:
            counts[1] += 1
            res.append("%s%s%s" % (REVERSE, pres.hostname, NORMAL))
        else:
            counts[0] += 1
            res.append(pres.hostname)
    return " ".join(res)+"\n%i up, %i down" % (counts[0], counts[1])
FORMATTERS["cell"] = frl_cell


def frl_ccell(resultlist, replies):
    """
    Format the resultlist as "compact cells"

    Each host is represented by "." (ping ok) or "!" (ping not ok)
    """
    counts = [0, 0]
    res = []
    for pres in resultlist:
        if pres.pstats.rxcount == "?" or replies > pres.pstats.rxcount:
            counts[1] += 1
            res.append("!")
        else:
            counts[0] += 1
            res.append(".")
    return "".join(res)+"\n%i up, %i down" % (counts[0], counts[1])
FORMATTERS["ccell"] = frl_ccell


def frl_updownlist(resultlist, replies):
    """
    Format the resultlist as three lines: one showing all up hosts, prefixed
    `UP:', one for all down hosts, prefixed `DOWN:' and one summary line, of
    the form `TOTALS: <x> up, <y> down'
    """
    uphosts = set()
    downhosts = set()
    upcount = 0
    downcount = 0
    res = []
    for pres in resultlist:
        if pres.pstats.rxcount == "?" or replies > pres.pstats.rxcount:
            downcount +=1
            downhosts.add(pres.hostname)
        else:
            upcount +=1
            uphosts.add(pres.hostname)

    res.append("UP: %s" % (",".join(uphosts)))
    res.append("DOWN: %s" % (",".join(downhosts)))
    res.append("TOTALS: %s up, %s down" % (upcount, downcount))
    return "\n".join(res)
FORMATTERS["updl"] = frl_updownlist


def formatresultlist(resultlist, style, replies):
    """Dispatch formatting of resultlist to the handler of the given style"""
    if style not in FORMATTERS:
        return "Unknown formatter '%s'" % (style)

    return FORMATTERS[style](resultlist, replies)


def main():
    """Main program: parse cmdline and call service functions"""
    global TERSE

    if "--version" in sys.argv or "-V" in sys.argv:
        print_version()
        sys.exit(0)

    cmdp = argparse.ArgumentParser(description=
                                   'Ping hosts in parallel and show results')
    cmdp.add_argument('targets', metavar='target', nargs='+',
                      help='Hostname or IPv4 to ping')
    cmdp.add_argument('--count', "-c", metavar='count', default=5, type=int,
                      help='Number of ICMP echo requests to send (%(default)s)')
    cmdp.add_argument('--replies', "-r", metavar='replies', default=4, type=int,
                      help='Minimum number of ping replies to expect before a '
                      'host is considered up (%(default)s).')
    cmdp.add_argument('--concurrency', "-n", metavar='number', default=100,
                      type=int,
                      help='Number of parallel processes to use (%(default)s). '
                      'Note: the actual number will be the minimum of this and '
                      'the number of hosts to ping')
    cmdp.add_argument('--mode', '-m', metavar='mode',
                       help='Output mode, one of %s (list)' %
                       (", ".join(FORMATTERS.keys())),
                       choices=FORMATTERS.keys(), default='list')
    cmdp.add_argument('--terse', '-t', default=False,
                      action="store_true", help='Terse output. This will not '
                      'output anything except whatever the result formatter '
                      '(mode) you chose does.')
    # This is here so it will show up in --help output
    cmdp.add_argument('--version', '-V', default=False,
                      action="store_true", help='Print version information and'
                      'exit with zero status.')
    cmdp.add_argument('--noadjust', '-a', default=False,
                      action="store_true", help='Do not adjust expected '
                      'number of replies, even if larger than number of '
                      'requests sent.')


    args = cmdp.parse_args()

    TERSE = args.terse
    concurrency = min(args.concurrency, len(args.targets))

    # Sanity check
    if (args.count < args.replies):
        eprint("Warning: Expected reply count is larger than number of "
               "requests sent (%i > %i)." % (args.replies, args.count))
        if not args.noadjust:
            eprint("Adjusting expected reply count to %i" % (args.count))
            args.replies = args.count
        else:
            eprint("All hosts will be marked as down.")

    eprint("Pinging %i machines with %i workers; %s pings per host" %
           (len(args.targets), concurrency, args.count))
    pool = Pool(processes=concurrency)
    start = time.time()
    ppinger = partial(pinger, count=args.count)
    results = pool.map(ppinger, args.targets)
    end = time.time()
    #print(results)
    print(formatresultlist(results, args.mode, args.replies))
    eprint("Time taken: %.3f seconds (%.3f per host)" %
          (end-start, (end-start)/len(args.targets)))


if __name__ == "__main__":
    main()
