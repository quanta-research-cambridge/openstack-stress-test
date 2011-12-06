"""Defines various ub-classes of the `TestCase` and
`PendingAction` class. The sub-classes of TestCase implement various
API calls on the Nova cluster having to do with Server Actions. Each
sub-class will have a corresponding PendingAction. These pending
actions veriy that the API call was successful or not."""

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

# system imports
import json
import random
import sys
import time

# import kong modules
import kong.nova
import kong.common
import kong.exceptions

# local imports
import test_case
import state
import pending_action
from basherexceptions import *
from utils.util import *
from utils.nova import *

class TestRebootVM(test_case.TestCase):
    """Reboot a server"""

    def run(self, connection, state, *pargs, **kwargs):
        """
        Send an HTTP POST request to the nova cluster to reboot a random
        server. Update state of object in `state` variable to indicate that
        it is rebooting.
        `connection` : object returned by kong.nova.API
        `state`      : `State` object describing our view of state of cluster
        `pargs`      : positional arguments
        `kwargs`     : keyword arguments, which include:
                       `timeout` : how long to wait before issuing Exception
                       `type`    : reboot type [SOFT or HARD] (default is SOFT)
        """

        vms = state.get_machines()
        active_vms = [v for k, v in vms.iteritems() if v and v[1] == 'ACTIVE']
        # no active vms, so return null
        if not active_vms:
            self._logger.info('no ACTIVE machines to reboot')
            return

        _reboot_type = kwargs.get('type', 'SOFT')
        _timeout = kwargs.get('timeout', 600)

        # select active vm to reboot and then send request to nova controller
        target = random.choice(active_vms)
        reboot_target = target[0]

        # allocate public address to this vm
        _ip_addr = allocate_ip(connection, reboot_target)

        reboot_body = { 'type': _reboot_type }
        post_body = json.dumps({'reboot' : reboot_body})
        url = '/servers/%s/action' % reboot_target['id']
        (response, body) = connection.request('POST',
                                              url,
                                              body=post_body)

        if (response.status != 202):
            self._logger.error("response: %s" % response)
            raise Exception

        if _reboot_type == 'SOFT':
            state_name = 'REBOOT'
        else:
            state_name = 'REBOOT' ### this is a bug, should be HARD_REBOOT

        self._logger.info('waiting for machine %s to change to %s' %
                          (reboot_target['id'], state_name))

        # check for state transition
        try:
            state_string = state_name
            connection.wait_for_server_status(
                reboot_target['id'], state_name, timeout=0
                )
        except AssertionError:
            # grab the actual state as we think it is
            temp_obj = state.get_machines()[self._target['id']]
            self._logger.debug(
                "machine %s in state %s" %
                (reboot_target['id'], temp_obj[1])
                )
            state_string = temp_obj[1]

        if state_string == state_name:
            self._logger.info('machine %s ACTIVE -> %s' %
                              (reboot_target['id'], state_name))
            state.set_machine_state(reboot_target['id'],
                                    (reboot_target, state_name))

        return VerifyRebootVM(connection,
                              state,
                              reboot_target,
                              timeout=_timeout,
                              reboot_type=_reboot_type,
                              state_name=state_string,
                              ip_addr=_ip_addr)

class VerifyRebootVM(pending_action.PendingAction):
    """Class to verify that the reboot completed."""
    States = enum('REBOOT_CHECK', 'ACTIVE_CHECK')

    def __init__(self, connection, state, target_server, 
                 timeout=600,
                 reboot_type=None,
                 state_name=None,
                 ip_addr=None):
        super(VerifyRebootVM, self).__init__(connection,
                                             state,
                                             target_server,
                                             timeout=timeout)
        self._ip_addr = ip_addr
        # FIX ME: this is a nova bug
        if reboot_type == 'SOFT':
            self._reboot_state = 'REBOOT'
        else:
            self._reboot_state = 'REBOOT' # should be HARD REBOOT

        if state_name == 'ACTIVE': # was still active, check to see if REBOOT
            self._retry_state = self.States.REBOOT_CHECK
        else: # was REBOOT, so now check for ACTIVE
            self._retry_state = self.States.ACTIVE_CHECK

    def retry(self):
        """
        Check to see that the server of interest has actually rebooted. Update
        state to indicate that server is running again.
        """
        # don't run reboot verification if target machine has been
        # deleted or is going to be deleted
        if (self._target['id'] not in self._state.get_machines().keys() or
            self._state.get_machines()[self._target['id']][1] == 'TERMINATING'):
            self._logger.debug('machine %s is deleted or TERMINATING' %
                               self._target['id'])
            return True

        if time.time() - self._start_time > self._timeout:
            raise TimeoutException

        if self._retry_state == self.States.REBOOT_CHECK:
            server_state = self._check_for_status(self._reboot_state)
            if server_state == self._reboot_state:
                self._logger.info('machine %s ACTIVE -> %s' %
                                  (self._target['id'], self._reboot_state))
                self._state.set_machine_state(self._target['id'],
                                              (self._target, self._reboot_state))
                self._retry_state = self.States.ACTIVE_CHECK
            elif server_state == 'ACTIVE':
                # machine must have gone ACTIVE -> REBOOT ->ACTIVE
                self._retry_state = self.States.ACTIVE_CHECK

        elif self._retry_state == self.States.ACTIVE_CHECK:
            if not self._check_for_status('ACTIVE'):
                return False

        server = self._connection.get_server(self._target['id'])

        # FIXME: fix the ssh.client thing
        # client = kong.common.ssh.Client(ip, 'ubuntu', admin_pass, 60)
        # if not client.test_connection_auth():
        #     self._logger.error('machine: %s, ip: %s, pwd: %s' %
        #                        (self._target['id'], ip, admin_pass))
        #     raise Exception
        self._logger.info('machine %s REBOOT -> ACTIVE [%.1f secs elapsed]' %
                              (self._target['id'], time.time() - self._start_time))
        self._state.set_machine_state(self._target['id'],
                                      (self._target, 'ACTIVE'))
        if self._ip_addr:
            deallocate_ip(self._connection, self._ip_addr)

        return True

class TestResizeVM(test_case.TestCase):
    """Resize a server (change flavors)"""

    def run(self, connection, state, *pargs, **kwargs):
        """
        Send an HTTP POST request to the nova cluster to resize a random
        server. Update `state` to indicate server is rebooting.

        `connection` : object returned by kong.nova.API
        `state`      : `State` object describing our view of state of cluster
        `pargs`      : positional arguments
        `kwargs`     : keyword arguments, which include:
                       `timeout` : how long to wait before issuing Exception
        """

        vms = state.get_machines()
        active_vms = [v for k, v in vms.iteritems() if v and v[1] == 'ACTIVE']
        # no active vms, so return null
        if not active_vms:
            self._logger.debug('no ACTIVE machines to resize')
            return

        target = random.choice(active_vms)
        resize_target = target[0]
        print resize_target

        _timeout = kwargs.get('timeout', 600)

        # determine current flavor type, and resize to a different type
        # m1.tiny -> m1.small, m1.small -> m1.tiny
        curr_size = int(resize_target['flavor']['id'])
        if curr_size == 1:
            new_size = 2
        else:
            new_size = 1
        flavor_type = { 'flavorRef': new_size } # resize to m1.small

        post_body = json.dumps({'resize' : flavor_type})
        url = '/servers/%s/action' % resize_target['id']
        (response, body) = connection.request('POST',
                                              url,
                                              body=post_body)

        if (response.status != 202):
            self._logger.error("response: %s" % response)
            raise Exception

        state_name = check_for_status(connection, resize_target, 'RESIZE')

        if state_name == 'RESIZE':
            self._logger.info('machine %s: ACTIVE -> RESIZE' %
                              resize_target['id'])
            state.set_machine_state(resize_target['id'],
                                    (resize_target, 'RESIZE'))

        return VerifyResizeVM(connection,
                              state,
                              resize_target,
                              state_name=state_name,
                              timeout=_timeout)

class VerifyResizeVM(pending_action.PendingAction):
    """Verify that resizing of a VM was successful"""
    States = enum('VERIFY_RESIZE_CHECK', 'ACTIVE_CHECK')

    def __init__(self, connection, state, created_server, 
                 state_name=None, 
                 timeout=300):
        super(VerifyResizeVM, self).__init__(connection,
                                             state,
                                             created_server,
                                             timeout=timeout)
        self._retry_state = self.States.VERIFY_RESIZE_CHECK
        self._state_name = state_name

    def retry(self):
        """
        Check to see that the server was actually resized. And change `state`
        of server to running again.
        """
        # don't run resize if target machine has been deleted
        # or is going to be deleted
        if (self._target['id'] not in self._state.get_machines().keys() or
            self._state.get_machines()[self._target['id']][1] == 'TERMINATING'):
            self._logger.debug('machine %s is deleted or TERMINATING' %
                               self._target['id'])
            return True

        if time.time() - self._start_time > self._timeout:
            raise TimeoutException

        if self._retry_state == self.States.VERIFY_RESIZE_CHECK:
            if self._check_for_status('VERIFY_RESIZE') == 'VERIFY_RESIZE':
                # now issue command to CONFIRM RESIZE
                post_body = json.dumps({'confirmResize' : null})
                url = '/servers/%s/action' % self._target['id']
                (response, body) = connection.request('POST',
                                                      url,
                                                      body=post_body)
                if (response.status != 204):
                    self._logger.error("response: %s" % response)
                    raise Exception

                self._logger.info(
                    'CONFIRMING RESIZE of machine %s [%.1f secs elapsed]' %
                    (self._target['id'], time.time() - self._start_time)
                    )
                state.set_machine_state(self._target['id'],
                                        (self._target, 'CONFIRM_RESIZE'))

                # change states
                self._retry_state = self.States.ACTIVE_CHECK

            return False

        elif self._retry_state == self.States.ACTIVE_CHECK:
            if not self._check_connection("ACTIVE"):
                return False
            else:
                server = self._connection.get_server(self._target['id'])

                # Find private IP of server?
                try:
                    (_, network) = server['addresses'].popitem()
                    ip = network[0]['addr']
                except KeyError:
                    self._logger.error(
                        'could not get ip address for machine %s' %
                        self._target['id']
                        )
                    raise Exception

                self._logger.info(
                    'machine %s: VERIFY_RESIZE -> ACTIVE [%.1f secs elapsed]' %
                    (self._target['id'], time.time() - self._start_time)
                    )
                self._state.set_machine_state(self._target['id'],
                                              (self._target, 'ACTIVE'))

                return True

        else:
            # should never get here
            self._logger.error('Unexpected state')
            raise Exception
