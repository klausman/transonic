#!/usr/bin/python3 -tt

# Copyright (C) 2011 Tobias Klausmann

import sys
import os
import subprocess

from multiprocessing import Pool

from collections import namedtuple

pingstats = namedtuple('pingstats', "txcount rxcount lossprc totaltm")
rttstats = namedtuple('rttstats', "rmin ravg rmax rmdev")

class Pingresult:
    def __init__(self, hostname="UNKNOWN", pstats=None, rtt=None, 
                 style="line"):
        self.hostname = hostname
        if pstats:
            self.pstats = pstats
        else:
            self.pstats = pingstats("?", "?", "?", "?")
        if rtt:
            self.rtt = rtt
        else:
            self.rtt = rttstats("?", "?", "?", "?")
        self.style = style

    def __str__(self):
        if self.style == "line":
            return ("%s S%s/R%s, maMD: %s/%s/%s/%s" % 
                (self.hostname, self.pstats.txcount, self.pstats.rxcount,
                 self.rtt.rmin, self.rtt.ravg, self.rtt.rmax, self.rtt.rmdev))
        else:
            return("Unknown style '%s' for '%s'" % (self.style, self.hostname))

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()

    pool = Pool(processes=4)
    results = pool.map(pinger, sys.argv[1:])
    #print(results)
    print("\n".join(str(x) for x in results))
