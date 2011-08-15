#!/usr/bin/python2 -tt
"""Transonic, a massively parallel host pinger and result displayer"""
# Copyright (C) 2011 Tobias Klausmann

import optparse
import subprocess
import sys
#import terminal
import time

from multiprocessing import Pool

from collections import namedtuple

RED = '\x1b[38;5;1m'
NORMAL = '\x1b[m\x1b(B'
YELLOW = '\x1b[38;5;3m'
REVERSE = '\x1b[7m'

__Pingstats__ = namedtuple('__Pingstats__', "txcount rxcount lossprc totaltm")
__RTTstats__ = namedtuple('__RTTstats__', "rmin ravg rmax rmdev")

class Pingresult:
    """Encapsulate one ping result, including RTT et al"""
    def __init__(self, hostname="UNKNOWN", pstats=None, rtt=None):
        self.hostname = hostname
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
    """Print fmt%args to stderr and add newline"""
    sys.stderr.write(fmt % args)
    sys.stderr.write("\n")

def pinger(host):
    """
    Ping host and return Pingresult
    """
    #print("Ping job with PID %i for host %s starting" % (os.getpid(), host))
    rtts = None
    pstat = None
    cmd = ['ping', '-c', str(count), '-q', host]
    pcomm = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
    output, _ = pcomm.communicate() # we drop stderr and ignore it

    # pylint gets confused here. pylint: disable-msg=E1103
    for line in output.split("\n"):
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
    res =  Pingresult(host, pstat, rtts)
    #print(res)
    return res

def formatresultlist(resultlist, style):
    """Format resultlist elements according to style setting"""
    counts = [0, 0]
    if style == "list":
        return "\n".join(str(x) for x in resultlist)

    elif style == "cell":
        res = []
        for pingresult in resultlist:
            if pingresult.pstats.txcount > pingresult.pstats.rxcount or \
               pingresult.pstats.rxcount == 0:
                counts[1] += 1
                res.append("%s%s%s" % (REVERSE, pingresult.hostname, NORMAL))
            else:
                counts[0] += 1
                res.append(pingresult.hostname)
        return " ".join(res)+"\n%i up, %i down" % (counts[0], counts[1])

    elif style == "ccell":
        res = []
        for pingresult in resultlist:
            if pingresult.pstats.txcount > pingresult.pstats.rxcount or \
               pingresult.pstats.rxcount == 0:
                counts[1] += 1
                res.append("!")
            else:
                counts[0] += 1
                res.append(".")
        return "".join(res)+"\n%i up, %i down" % (counts[0], counts[1])

def sglob(*globs):
    """Set per-worker globals"""
    global count
    count = globs[0]

def main():
    """Main program: parse cmdline and call service functions"""
    modes = ['cell', 'ccell', 'list']
    cmdp = optparse.OptionParser()
    cmdp.add_option('--count', "-c", metavar='count', default=5, type=int,
                    help='Number of ICMP echo requests to send (5)')
    cmdp.add_option('--concurrency', "-n", metavar='number', default=100, 
                    type=int, help='Number of parallel processes to use (100)')
    cmdp.add_option('--mode', '-m', metavar='mode', 
                    help='Output mode, one of %s (list)' % (", ".join(modes)),
                    choices=modes, default='list')

    opts, arguments = cmdp.parse_args()

    concurrency = min(opts.concurrency, len(arguments))

    #terminal.setup()
    eprint("Pinging %i machines with %i workers; %s pings per host." % 
           (len(arguments), concurrency, opts.count))
    pool = Pool(processes=concurrency, initializer=sglob, initargs=[opts.count])
    start = time.time()
    results = pool.map(pinger, arguments)
    end = time.time()
    #print(results)
    print(formatresultlist(results, style=opts.mode))
    eprint("Time taken: %.2f seconds (%.3f per host)" % 
           (end-start, (end-start)/len(arguments)))

if __name__ == "__main__":
    main()
