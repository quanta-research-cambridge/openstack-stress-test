"""A class to store the state of various persistent objects in the Nova 
cluster, e.g. machines, volumes.  Use methods to query to state which than 
can be compared to the current state of the objects in Nova"""

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

class State(dict):
    def __init__(self, *pargs, **kwargs):
        self._max_vms = kwargs.get('max_vms', 32)
        self._machines = {}
        self._volumes = {}

    # machine state methods
    def get_machines(self):
        """return the machines dictionary that we believe are in the cluster."""
        return self._machines

    def get_max_machines(self):
        """return the maximum number of machines we can create."""
        return self._max_vms

    def set_machine_state(self, key, val):
        """Store `val` in the dictionary indexed at `key`."""
        if not val:
            del self._machines[key]
        self._machines[key] = val
