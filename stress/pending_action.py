"""Describe follow-up actions using `PendingAction` class to verify
that nova API calls such as create/delete are completed"""

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

__author__ = "Eugene Shih"

import logging
import time
import abc

class PendingAction(object):
    """
    Initialize and describe actions to verify that a Nova API call
    is successful.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, nova_connection, state, target_server, timeout=600):
        """
        `nova_connection` : object returned by `kong.nova.API`
        `state`           : externally maintained data structure about
                            state of VMs or other persistent objects in
                            the nova cluster
        `target_server`   : server that we actions were performed on
        `target_server`   : time before we declare a TimeoutException
        `pargs`           : positional arguments
        `kargs`           : keyword arguments
        """
        self._connection = nova_connection
        self._state = state
        self._target = target_server

        self._logger = logging.getLogger(self.__class__.__name__)
        self._start_time = time.time()
        self._timeout = timeout

    def _check_for_status(self, state_string):
        """Check to see if the machine has transitioned states"""
        t1 = time.time() # for debugging
        try:
            self._connection.wait_for_server_status(
                self._target['id'],
                state_string,
                timeout=0
                )
        except AssertionError:
            # grab the actual state as we think it is
            temp_obj = self._state.get_machines()[self._target['id']]
            self._logger.debug("machine %s in state %s" %
                               (self._target['id'],temp_obj[1]))
            self._logger.debug('%s, time: %d' % (temp_obj[1], time.time() - t1))
            return temp_obj[1]
        self._logger.debug('%s, time: %d' % (state_string, time.time() - t1))
        return state_string

    @abc.abstractmethod
    def retry(self):
        """Invoked by user of this class to verify completion of"""
        """previous TestCase actions"""
        return False
