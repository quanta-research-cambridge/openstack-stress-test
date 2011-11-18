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

import logging
import time
import abc

class PendingAction(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, nova_connection, state, target_server, timeout=600):
        self._connection = nova_connection
        self._state = state
        self._target = target_server

        self._logger = logging.getLogger(self.__class__.__name__)
        self._start_time = time.time()
        self._timeout = timeout

    def _check_for_status(self, state_string):
        """Check to see if the machine has transitioned states"""
        try:
            self._connection.wait_for_server_status(
                self._target['id'],
                state_string,
                timeout=0
                )
        except AssertionError:
            # grab the actual state as we think it is
            temp_obj = self._state.get_machines()[self._target['id']]
            self._logger.debug(
                "machine %s in state %s" %
                (self._target['id'],
                 temp_obj[1])
                )
            return temp_obj[1]
        return state_string

    @abc.abstractmethod
    def retry(self):
        """Invoked by user of this class to verify completion of"""
        """previous TestCase actions"""
        return False
