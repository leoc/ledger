#!/usr/bin/env python

import sys
import os
import re

from subprocess import Popen, PIPE

class LedgerHarness:
    ledger    = None
    succeeded = 0
    failed    = 0
    verify    = False
    gmalloc   = False

    def __init__(self, argv):
        if not os.path.isfile(argv[1]):
            print "Cannot find ledger at '%s'" % argv[1]
            sys.exit(1)

        self.ledger    = argv[1]
        self.succeeded = 0
        self.failed    = 0
        self.verify    = '--verify' in argv
        self.gmalloc   = '--gmalloc' in argv

    def run(self, command, verify=None, gmalloc=None, columns=True):
        env = os.environ.copy()

        if (gmalloc is not None and gmalloc) or \
           (gmalloc is None and self.gmalloc):
            env['MallocGuardEdges']      = '1'
            env['MallocScribble']        = '1'
            env['MallocPreScribble']     = '1'
            env['MallocCheckHeapStart']  = '100'
            env['MallocCheckHeapEach']   = '100'
            env['DYLD_INSERT_LIBRARIES'] = '/usr/lib/libgmalloc.dylib'
            env['MALLOC_PROTECT_BEFORE'] = '1'
            env['MALLOC_FILL_SPACE']     = '1'
            env['MALLOC_STRICT_SIZE']    = '1'

        if (verify is not None and verify) or \
           (verify is None and self.verify):
            insert = ' --verify'
        else:
            insert = ''

        if columns:
            insert += ' --columns=80'

        command = re.sub('\$ledger',
                         '%s%s --args-only' % (self.ledger, insert),
                         command)

        return Popen(command, shell=True, close_fds=True, env=env,
                     stdin=PIPE, stdout=PIPE, stderr=PIPE)

    def read(self, fd):
        text = ""
        text_data = os.read(fd.fileno(), 8192)
        while text_data:
            if text_data:
                text += text_data
            text_data = os.read(fd.fileno(), 8192)
        if text_data:
            text += text_data
        return text

    def readlines(self, fd):
        lines = []
        for line in fd.readlines():
            if line == "GuardMalloc: Allocations will be placed on byte boundaries.\n" or \
               line == "GuardMalloc:  - Some buffer overruns may not be noticed.\n" or \
               line == "GuardMalloc:  - Applications using vector instructions (e.g., SSE or Altivec) may fail.\n" or \
               line == "GuardMalloc:  - Applications expecting word-aligned pointers may fail (such as Carbon applications)\n" or \
               line == "GuardMalloc: GuardMalloc version 18\n":
                continue
            else:
                lines.append(line)
        return lines

    def wait(self, process, msg='Ledger invocation failed:'):
        if process.wait() != 0:
            print msg
            print process.stderr.read()
            self.failure()
            return False
        return True

    def success(self):
        sys.stdout.write(".")
        self.succeeded += 1

    def failure(self):
        sys.stdout.write("E")
        self.failed += 1

    def exit(self):
        print
        if self.succeeded > 0:
            print "OK (%d) " % self.succeeded,
        if self.failed > 0:
            print "FAILED (%d)" % self.failed,
        print

        sys.exit(self.failed)

if __name__ == '__main__':
    harness = LedgerHarness(sys.argv)
    proc = harness.run('$ledger -f doc/sample.dat reg')
    print 'STDOUT:'
    print proc.stdout.read()
    print 'STDERR:'
    print proc.stderr.read()
    harness.success()
    harness.exit()
