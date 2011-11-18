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
        vms = state.get_machines()
        active_vms = [v for k, v in vms.iteritems() if v and v[1] == 'ACTIVE']
        # no active vms, so return null
        if not active_vms:
            self._logger.info('no ACTIVE machines to reboot')
            return

        reboot_type = kwargs.get('type', 'SOFT')
        _timeout = kwargs.get('timeout', 600)

        # allocate public address to this vm
        _ip_addr = allocate_ip(connection)

        # select active vm to reboot and then send request to nova controller
        target = random.choice(active_vms)
        reboot_target = target[0]
        reboot_body = { 'type': reboot_type }
        post_body = json.dumps({'reboot' : reboot_body})
        url = '/servers/%s/action' % reboot_target['id']
        (response, body) = connection.request('POST',
                                              url,
                                              body=post_body)

        if (response.status != 202):
            self._logger.error("response: %s" % response)
            raise Exception

        if reboot_type == 'SOFT':
            state_name = 'REBOOT'
        else:
            state_name = 'REBOOT' ### this is a bug, should be HARD_REBOOT

        self._logger.info('waiting for machine %s to change to %s' %
                          (reboot_target['id'], state_name))

        # this will throw an exception if timeout is exceeded
        connection.wait_for_server_status(reboot_target['id'],
                                          state_name,
                                          timeout=_timeout)

        self._logger.info('machine %s ACTIVE -> REBOOT' %
                          reboot_target['id'])
        state.set_machine_state(reboot_target['id'],
                                (reboot_target, 'REBOOT'))
        return VerifyRebootVM(connection,
                              state,
                              reboot_target,
                              timeout=_timeout,
                              ip_addr=_ip_addr)

class VerifyRebootVM(pending_action.PendingAction):

    def __init__(self, connection, state, target_server, timeout=600, ip_addr=None):
        super(VerifyRebootVM, self).__init__(connection,
                                             state,
                                             target_server,
                                             timeout=timeout)
        self._ip_addr = ip_addr

    def retry(self):
        # don't run reboot verification
        # if target machine has been deleted or is going to be deleted
        if (self._target['id'] not in self._state.get_machines().keys() or
            self._state.get_machines()[self._target['id']] == 'TERMINATING'):
            self._logger.debug('machine %s is deleted or TERMINATING' %
                               self._target['id'])
            return True

        if time.time() - self._start_time > self._timeout:
            raise TimeoutException

        if not self._check_for_status('ACTIVE'):
            return False

        server = self._connection.get_server(self._target['id'])

        # FIXME: fix the ssh.client thing
        # client = kong.common.ssh.Client(ip, 'ubuntu', admin_pass, 60)
        # if not client.test_connection_auth():
        #     self._logger.error('machine: %s, ip: %s, pwd: %s' %
        #                        (self._target['id'], ip, admin_pass))
        #     raise Exception

        if self._ip_addr:
            deallocate_ip(self._connection, self._ip_addr)

        self._logger.info('machine %s REBOOT -> ACTIVE [%.1f secs elapsed]' %
                          (self._target['id'], time.time() - self._start_time))
        self._state.set_machine_state(self._target['id'],
                                      (self._target, 'ACTIVE'))
        return True

class TestResizeVM(test_case.TestCase):
    """Resize a server (change flavors)"""

    def run(self, connection, state, *pargs, **kwargs):
        vms = state.get_machines()
        active_vms = [v for k, v in vms.iteritems() if v and v[1] == 'ACTIVE']
        # no active vms, so return null
        if not active_vms:
            self._logger.debug('no ACTIVE machines to resize')
            return

        target = random.choice(active_vms)
        resize_target = target[0]
        print resize_target

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

        connection.wait_for_server_status(resize_target['id'],
                                                'RESIZE',
                                                timeout=120)

        self._logger.info('machine %s: ACTIVE -> RESIZE' %
                          resize_target['id'])
        state.set_machine_state(resize_target['id'],
                                (resize_target, 'RESIZE'))
        return VerifyResizeVM(connection,
                              state,
                              resize_target)

class VerifyResizeVM(pending_action.PendingAction):

    States = enum('VERIFY_RESIZE_CHECK', 'ACTIVE_CHECK')

    def __init__(self, connection, state, created_server, timeout=300):
        super(VerifyResizeVM, self).__init__(connection,
                                             state,
                                             created_server,
                                             timeout=timeout)
        self._retry_state = self.States.VERIFY_RESIZE_CHECK

    def retry(self):
        # don't run resize if target machine has been deleted
        # or is going to be deleted
        if (self._target['id'] not in self._state.get_machines().keys() or
            self._state.get_machines()[self._target['id']] == 'TERMINATING'):
            self._logger.debug('machine %s is deleted or TERMINATING' %
                               self._target['id'])
            return True

        if time.time() - self._start_time > self._timeout:
            raise TimeoutException

        if self._retry_state == self.States.VERIFY_RESIZE_CHECK:
            if self._check_for_status("VERIFY_RESIZE"):
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
