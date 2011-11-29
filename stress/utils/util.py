# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 Quanta Research Cambridge, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from subprocess import *
import shlex
import os
import logging

if not os.environ['NOVA_SSH_KEY_PATH']:
    print >> sys.stderr, "NOVA_SSH_KEY_PATH environment variable not set."
    raise Exception

SSH_OPTIONS = (" -q" +
               " -o UserKnownHostsFile=/dev/null" +
               " -o StrictHostKeyChecking=no -i %s" %
               os.environ['NOVA_SSH_KEY_PATH'])

def scp(args):
    return check_call(shlex.split("scp" + SSH_OPTIONS + args))

def execute(command, check=True):
    popenargs = shlex.split(command)
    process = Popen(popenargs, stdout=PIPE)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode and check:
        logging.error("%s failed with retcode: %s" % (command, retcode))
        raise Exception

    return output

def ssh(node, command, check=True):
    command = "ssh %s root@%s %s" % (SSH_OPTIONS, node, command)
    popenargs = shlex.split(command)
    process = Popen(popenargs, stdout=PIPE)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode and check:
        logging.error("%s: ssh failed with retcode: %s" % (node, retcode))
        raise Exception
    return output

def execute_on_all(nodes, command):
    for node in nodes:
        ssh(node, command)

def enum(*sequential, **named):
    """Create auto-incremented enumerated types"""
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)
