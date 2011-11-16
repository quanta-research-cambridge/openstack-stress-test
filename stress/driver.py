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

import random
import datetime
import logging
import os
import stat
import sys
import json
import uuid
import time

# import kong modules
# Make sure you add openstack-integration-tests to your PYTHONPATH
import kong.nova

# local imports
from test_case import *
from basher import BasherChoice
from basherexceptions import *
from state import State
import utils.env
import utils.util

# setup logging to file
logging.basicConfig(
    format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
    datefmt='%m-%d %H:%M:%S',
    filename="debug.log",
    level=logging.DEBUG)

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-20s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

def create_cases(choice_spec):
    cases = []
    count = 0
    for choice in choice_spec:
        p = choice.probability
        for i in range(p):
            cases.append(choice)
        i = i + p
        count = count + p
    assert(count == 100)
    return cases

def get_compute_nodes():
    nodes = []
    lines = utils.util.ssh(utils.env.NOVA_HOST,
                     "nova-manage service list | fgrep nova-compute").\
                     split('\n')
    # For example: nova-compute xg11eth0 nova enabled :-) 2011-10-31 18:57:46
    for line in lines:
        words = line.split()
        if len(words) > 0:
            nodes.append(words[1])
    return nodes

def error_in_logs(nodes):
    for node in nodes:
        errors = utils.util.ssh(node,
                                'egrep "ERROR\|TRACE" /var/log/nova/*.log',
                                check=False)
        if len(errors) > 0:
            logging.error('%s: %s', (node, errors))
            return False
    return False

def bash_openstack(connection,
                   choice_spec,
                   *pargs,
                   **kwargs):

    # get keyword arguments
    duration=kwargs.get('duration', datetime.timedelta(seconds=10))
    seed=kwargs.get('seed', 1)
    sleep_time=kwargs.get('sleep_time', 3)
    max_vms=kwargs.get('max_vms', 32)

    computes = get_compute_nodes()
    utils.util.execute_on_all(computes, "rm -f /var/log/nova/*.log")
    random.seed(seed)
    cases = create_cases(choice_spec)
    test_end_time = time.time() + duration.seconds
    state = State(max_vms=max_vms)

    retry_list = []
    last_retry = time.time()
    cooldown = False
    logcheck_count = 0
    test_succeeded = True
    while True:
        if not cooldown:
            if time.time() < test_end_time:
                case = random.choice(cases)
                retry = case.invoke(connection, state)
                if retry != None:
                    retry_list.append(retry)
            else:
                logging.info('Cooling down...')
                cooldown = True
        if cooldown and len(retry_list) == 0:
            if error_in_logs(computes):
                test_succeeded = False
            break
        # Retry verifications every 5 seconds.
        if time.time() - last_retry > 5:
            logging.debug('retry verifications %d tasks', len(retry_list))
            new_retry_list = []
            for v in retry_list:
                if not v.retry():
                    new_retry_list.append(v)
            retry_list = new_retry_list
            last_retry = time.time()
        time.sleep(sleep_time)
        # Check error logs after 100 actions
        if logcheck_count > 100:
            if error_in_logs(computes):
                test_succeeded = False
                break
            else:
                logcheck_count = 0
        else:
            logcheck_count = logcheck_count + 1
    # Cleanup
    logging.info('Cleaning up: terminating virtual machines...')
    vms = state.get_machines()
    active_vms = [v for k, v in vms.iteritems() if v and v[1] == 'ACTIVE']
    for target in active_vms:
        kill_target = target[0]
        connection.delete_server(kill_target['id'])
        # check to see that the server was actually killed
        try:
            url = '/servers/%s' % kill_target['id']
            connection.poll_request_status('GET', url, 404, timeout=60)
        except TimeoutException:
            raise
        logging.info('killed %s' % kill_target['id'])
        state.set_machine_state(kill_target['id'], None)

    return test_succeeded
