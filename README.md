# Transonic

Transonic is a simple script that lets you run ping(1) in a massively parallel
manner. The only limits are your bandwidth and the performance of the computer
you run it on. After all pings have run, Transonic will present the results in
one of several formats. Some of the formats drop detail (like RTT) in favour of
being able to present you a bird's eye view of the state of hosts pinged.

Transonic falls into a rather small niche. It is not meant to replace fping,
which is fast (except for DNS, which it does serially), but it doesn't have
the rich output options transonic has. Nmap, while much more flexible
regarding output, is a tool that needs root privileges to do a proper ICMP
ECHO scan -- it defaults to doing a TCP pingscan instead. SUID bits on nmap
are extremely unlikely. Also, ping tends to be available on any machine with a
network connection -- fping and nmap might not be. The latter also goes for
many other diagnostic tools like netwox/wag. Aside from Python 2.6 or later,
transonic only depends on having ping(1) available. Finally, transonic is
written as simple as possible and thus is easier to adapt and extend according
to your taste than nmap or fping (and most other tools).

## Output modes

Currently, Transonic supports four output modes: `cell`, `ccell`, `updl` and
`list`, defaulting to `list`.

Here's an example of list output:

```
$ transonic.py localhost fw host.doesnotexist.invalid
Pinging 3 machines with 3 workers; 5 pings per host
localhost S5/R5, maMD: 0.018/0.026/0.030/0.007
fw S5/R5, maMD: 28.525/36.897/48.839/8.450
host.doesnotexist.invalid S?/R?, maMD: ?/?/?/?
Time taken: 4.107 seconds (1.369 per host)
```

Transonic shows one line per host pinged, plus a header line and a summary.
Every per-host line consist of the following:

`hostname, S<s>/S<r>, maMD: <numbers>`

`s` and `r` are the number of packets sent and received, respectively. The numbers
at the end of the line are the min, average, max round-trip time plus the
standard deviation of all the RTTs. All of these numbers are calculated by
`ping(1)` itself, so its documentation (and source) should be consulted if
details are needed.

The `cell` and `ccell` modes are very similar, here's an example of `cell`:

```
Pinging 3 machines with 3 workers; 5 pings per host
localhost fw.i-no.de host.doesnotexist.invalid
2 up, 1 down
Time taken: 4.050 seconds (1.350 per host)
```

Where "host.doesnotexist.invalid" is in reverse video (not easily reproducible
in this text file). This takes up less screen space than the per-line mode,
especially if the host names used are short. It will still tell you _which_
hosts are up/down.

The `ccell` ("condensed cell") mode forgoes telling you which hosts are up/down
in favour of displaying state of more hosts in the same amount of screen
space. It is most useful when pinging tens or even hundreds of hosts and
getting a quick view of the shape of things. Here's an example, also
demonstrating the `-c` and `-n` commandline options (output has been trimmed):

```
$ transonic.py -m ccell -c2 -n500 $IPS
Warning: Expected reply count is larger than number of requests sent (4 > 2).
Adjusting expected reply count to 2
Pinging 2816 machines with 500 workers; 2 pings per host
!!!!!!!!!!!!!!!!!!!!.!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!.!!!!.!.!!!.....!...!..!!!!!!!!!!.!.
....!..!!!!!!!!!!!!!!!..!!.!!!!!!!!!!!!!!!!!!!!!!!!!...!!!!!!!!!!.!..!...!!!!!
!!!..!!!!!!!.!!!!!.!!!!.!!!!!.!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!.!.!!!!!!!!!!!!!!!!!.!!!!!!!!!!.!!!!!!!!!!!!!!!!!!!!!!.!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
85 up, 2731 down Time taken: 66.269 seconds (0.024 per host)
```

Every host that is up is denoted by a `.` and every down host is denoted with
a `!`. Due to the way Transonic works, the order of hosts in the output is
basically random. Also note how Transonic will adjust the expected reply
count for you when it makes sense. This behaviour can be controlled using the
`-a` commandline flag.

The `updl` formatter will give you three lines, one with `UP:` and the hostnames
that are up; one with `DOWN:`, for down hosts and a summary line prefixed with
`TOTALS:`.

Writing your own output formatter is relatively easy if you know Python. Since
the Pinger function does all the `ping(1)` output parsing for you, all you need
to know is how to handle the Pingresult objects. If you come up with a
smashing new output formatter that is of general use, feel free to send me a
patch (note: Transonic is GPL-2), but note the comment about 2.x/3.x
compatibility below.

## Performance

Transonic is quite fast, as you can see from the example above. If you limit
the count of pings to 1 and crank up the count of workers (a modern machine
can easily handle 500 of them), Transonic will take very little time to
complete. Also, the more hosts are up and respond quickly, the quicker it will
be done.

Be careful with the number of workers, though. Transonic does not care how
much RAM you have or how fast your machine is. If you tell it to spawn 10000
workers to ping 20000 machines, it will happily consume all the RAM you have.
That said, Transonic will never spawn more workers than the number of targets
you provide.

Also, Transonic has the potential to quickly fill your network connection. A
corollary to that is that the admin of the net you're pinging might be very
unhappy with the amount of traffic you cause. Since Transonic won't (and
can't) mask the fact that _you_ cause the traffic, said Admin might take
(possibly legal) action against you. Don't do anything stupid, alright?

## Dependencies

Transonic currently assumes that `ping(1)` has the same output format that ping
from Linux' iputils has. If you have reasonably modern Linux installation,
this should be enough. If you run BSD or another shape of Unix, adjustments to
the Pinger function in Transonic may be necessary. Autodetection of what your
ping flavour is is _not_ planned.

## Python 2.x and 3.x

Transonic comes in two variants: one for Python 2.x with x>=6, named
`transonic2.py` in the distribution and one for Python 3.x with x>=2, named
`transonic.py`. Principal development is done using the version for 3.x, with
changes backported to the 2.x whenever feasible. So far, they are functionally
identical. If you send patches for Transonic, please make a reasonable effort
to write code that works with both versions with as little (read: no) editing
as possible.
