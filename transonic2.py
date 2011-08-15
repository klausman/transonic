#!/usr/bin/python2 -tt

# Copyright (C) 2011 Tobias Klausmann

import optparse
import os
import subprocess
import sys
#import terminal
import time

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

def set_pingcount(func):
    return 

def pinger(host):
    #print("Ping job with PID %i for host %s starting" % (os.getpid(), host))
    rtts = None
    pstat = None
    cmd = ['ping', '-c', str(opts.count), '-q', host]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, stderr = p.communicate()

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

def formatresults(results, style):
    counts = [0, 0]
    if style == "list":
        return "\n".join(str(x) for x in results)

    elif style == "cell":
        res = []
        for r in results:
            if r.pstats.txcount > r.pstats.rxcount or \
               r.pstats.rxcount == 0:
               counts[1] += 1
               res.append("%s%s%s" % (REVERSE, r.hostname, NORMAL))
            else:
               counts[0] += 1
               res.append(r.hostname)
        return " ".join(res)+"\n%i up, %i down" % (counts[0], counts[1])

    elif style == "ccell":
        res = []
        for r in results:
            if r.pstats.txcount > r.pstats.rxcount or \
               r.pstats.rxcount == 0:
               counts[1] += 1
               res.append("!")
            else:
               counts[0] += 1
               res.append(".")
        return "".join(res)+"\n%i up, %i down" % (counts[0], counts[1])

if __name__ == "__main__":
    global opts, args
    modes = ['cell', 'ccell', 'list']
    parser = optparse.OptionParser()
    parser.add_option('--count', "-c", metavar='count', default=5, type=int,
                       help='Number of ICMP echo requests to send (5)')
    parser.add_option('--concurrency', "-n", metavar='number', default=100, type=int,
                       help='Number of parallel processes to use (100)')
    parser.add_option('--mode', '-m', metavar='mode', 
                        help='Output mode, one of %s (list)' % 
                        (", ".join(modes)),
                        choices=modes, default='list')


    opts, args = parser.parse_args()

    #terminal.setup()
    eprint("Pinging %i machines with %i workers." % (len(args), opts.concurrency))
    pool = Pool(processes=opts.concurrency)
    start = time.time()
    results = pool.map(pinger, args)
    end = time.time()
    #print(results)
    print(formatresults(results, style=opts.mode))
    eprint("Time taken: %.2f seconds (%.3f per host)" %
           (end-start, (end-start)/len(args)))
