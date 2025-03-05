#!/usr/bin/env python

from datetime import timedelta
from subprocess import check_output
import platform

def _kb_str_to_mb(str):
    """Converts a string formatted like "1234 kB" into a string where value given is expressed in megabytes"""
    if str.lower().endswith('kb'):
        value = str[:-2].rstrip()
        mb_value = int(value)/1024.0
        return int(mb_value)
    else:
        raise ValueError("{} is not a kb string!".format(str))

def linux_info():
    info = {}
    uname = platform.uname()
    arguments = ["system", "hostname", "k_release", "version", 'machine', 'cpu']
    for i, element in enumerate(uname):
        info[arguments[i]] = element
    try:
        info["distribution"] = platform.linux_distribution()
    except:
        pass
    return info


"""
>>>cat /proc/cpuinfo
  MemTotal:         948012 kB
  MemFree:          719432 kB
  MemAvailable:     826740 kB
  Buffers:           16520 kB
  Cached:           115056 kB
SwapCached:            0 kB
Active:           121120 kB
Inactive:          72412 kB
Active(anon):      62448 kB
Inactive(anon):     7112 kB
Active(file):      58672 kB
Inactive(file):    65300 kB
Unevictable:           0 kB
Mlocked:               0 kB
  SwapTotal:        102396 kB
  SwapFree:         102396 kB
Dirty:                16 kB
Writeback:             0 kB
AnonPages:         61960 kB
Mapped:            55608 kB
  Shmem:              7600 kB
Slab:              16012 kB
SReclaimable:       7628 kB
SUnreclaim:         8384 kB
KernelStack:        1344 kB
PageTables:         2308 kB
NFS_Unstable:          0 kB
Bounce:                0 kB
WritebackTmp:          0 kB
CommitLimit:      576400 kB
Committed_AS:     647044 kB
VmallocTotal:    1105920 kB
VmallocUsed:        5132 kB
VmallocChunk:     878076 kB
CmaTotal:           8192 kB
CmaFree:            3476 kB
"""

def parse_proc_meminfo():
    """ Parses /proc/meminfo and returns key:value pairs"""
    meminfo_dict = {}
    with open("/proc/meminfo") as f:
        for line in f.readlines():
            try:
                key, value = line.split(":")
            except:
                continue
            else:
                meminfo_dict[key] = int(value.strip('\n').strip(' ').split(" ")[0])
    return meminfo_dict


"""
>>>free
             total       used       free     shared    buffers     cached
Mem:        948012     228680     719332       7600      16520     115056
-/+ buffers/cache:      97104     850908
Swap:       102396          0     102396
"""

def free(in_mb=True):
    memory_dict = {}
    meminfo_dict = parse_proc_meminfo()
    if in_mb:
        for key in meminfo_dict:
            meminfo_dict[key] = round(meminfo_dict[key]/1024, 2)
    mem_free = meminfo_dict["MemFree"]
    mem_total = meminfo_dict["MemTotal"]
    memory_dict["Total"] = mem_total
    memory_dict["Free"] = mem_free
    memory_dict["Used"] = mem_total-mem_free
    mem_buffers = meminfo_dict["Buffers"]
    mem_cache = meminfo_dict["Cached"]
    mem_shared = meminfo_dict["Shmem"]
    memory_dict["Buffers"] = mem_buffers
    memory_dict["Cached"] = mem_cache
    memory_dict["Shared"] = mem_shared
    memory_dict["UsedBC"] = mem_total-mem_free-mem_buffers-mem_cache
    memory_dict["FreeBC"] = mem_free+mem_buffers+mem_cache
    swap_free = meminfo_dict["SwapFree"]
    swap_total = meminfo_dict["SwapTotal"]
    memory_dict["SwapFree"] = swap_free
    memory_dict["SwapTotal"] = swap_total
    memory_dict["SwapUsed"] = swap_total-swap_free
    return memory_dict


"""
>>>cat /proc/uptime
5996.67 23683.61
"""

def uptime_timedelta():
    """Returns system uptime timedelta"""
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
        delta = timedelta(seconds = int(uptime_seconds))
    return delta


"""
>>>uptime 
 04:38:56 up  1:38,  2 users,  load average: 0.03, 0.08, 0.08
"""

def uptime():
    """Returns str(uptime_timedelta)"""
    return str(uptime_timedelta())
    

"""
>>>cat /proc/loadavg
0.03 0.08 0.08 2/189 1502
"""

def loadavg():
    with open('/proc/loadavg', 'r') as f:
        load1, load5, load15, ksch, last_pid = f.readline().strip('\n').split(" ")
    load1, load5, load15 = (float(var) for var in [load1, load5, load15])
    return (load1, load5, load15)
           

"""
processor	: 0
model name	: ARMv7 Processor rev 4 (v7l)
BogoMIPS	: 38.40
Features	: half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32 
CPU implementer	: 0x41
CPU architecture: 7
CPU variant	: 0x0
CPU part	: 0xd03
CPU revision	: 4

processor	: 1
#...

Hardware	: BCM2709
Revision	: a02082
Serial		: 00000000f6570ff1

"""

def cpu_info():
    """Parses /proc/cpuinfo and returns a dictionary made from its contents.
    Bug: for multiple processor definitions, returns only definition for the last processor."""
    info_dict = {}
    with open("/proc/cpuinfo", 'r') as f:
        contents = f.readlines()
        for line in contents:
            line = line.strip('\n').strip(' ')
            if line:
                key, value = [element.strip(' ').strip('\t') for element in line.split(":", 1)]
                info_dict[key] = value
    return info_dict

def is_raspberry_pi(cpuinfo = None):
    if not cpuinfo:
        cpuinfo = cpu_info()
        if "BCM270" in cpuinfo["Hardware"]:
            return True
    return False



if __name__ == "__main__":
    print(linux_info())
    print(cpu_info())
    print(is_raspberry_pi())
    print(free())
    print(uptime())
    print(loadavg())








