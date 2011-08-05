#!/usr/bin/python3 -tt

# Copyright (C) 2011 Tobias Klausmann

import sys
import os
import subprocess
#import terminal

from multiprocessing import Pool

from collections import namedtuple

RED='\x1b[38;5;1m'
NORMAL='\x1b[m\x1b(B'
YELLOW='\x1b[38;5;3m'
REVERSE='\x1b[7m'


pingstats = namedtuple('pingstats', "txcount rxcount lossprc totaltm")
rttstats = namedtuple('rttstats', "rmin ravg rmax rmdev")

class Pingresult:
    def __init__(self, hostname="UNKNOWN", pstats=None, rtt=None):
        self.hostname = hostname
        if pstats:
            self.pstats = pstats
        else:
            self.pstats = pingstats("?", "?", "?", "?")
        if rtt:
            self.rtt = rtt
        else:
            self.rtt = rttstats("?", "?", "?", "?")

    def __str__(self):
        return ("%s S%s/R%s, maMD: %s/%s/%s/%s" % 
            (self.hostname, self.pstats.txcount, self.pstats.rxcount,
             self.rtt.rmin, self.rtt.ravg, self.rtt.rmax, self.rtt.rmdev))

def eprint(fmt, *args):
    sys.stderr.write(fmt % args)
    sys.stderr.write("\n")

def usage():
    eprint("Usage goes here")
    sys.exit(0)

def pinger(host):
    #print("Ping job with PID %i for host %s starting" % (os.getpid(), host))
    rtts = None
    pstat = None
    cmd = "ping -c 5 -q '%s'" % (host)
    (retval, output) = subprocess.getstatusoutput(cmd)

    for line in output.split("\n"):
        #print(line)
        if line[2:2+len("packets transmitted")] == "packets transmitted":
            stats = line.split()
            if "errors," in stats:
                pstat = pingstats(int(stats[0]), int(stats[3]),
                                  int(stats[7][:-1]), int(stats[11][:-2]))
            else:
                pstat = pingstats(int(stats[0]), int(stats[3]),
                                  int(stats[5][:-1]), int(stats[9][:-2]))
            continue

        if line.startswith("rtt min/avg/max/mdev"):
            rtts = line.split(None, 4)[3]
            r_min, r_avg, r_max, r_mdev = rtts.split("/")
            rtts = rttstats(r_min, r_avg, r_max, r_mdev)
            continue
    res =  Pingresult(host, pstat, rtts)
    #print(res)
    return res

def formatresults(results, style="lines"):

    if style == "lines":
        return "\n".join(str(x) for x in results)

    elif style == "cells":
        res = []
        for r in results:
            if r.pstats.txcount > r.pstats.rxcount or \
               r.pstats.rxcount == 0:
               res.append("%s%s%s" % (REVERSE, r.hostname, NORMAL))
            else:
               res.append(r.hostname)
        return " ".join(res)



if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
    #terminal.setup()
    pool = Pool(processes=4)
    results = pool.map(pinger, sys.argv[1:])
    #print(results)
    print(formatresults(results, style="cells"))
