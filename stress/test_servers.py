"""Defines various ub-classes of the `TestCase` and
`PendingAction` class. The sub-classes of TestCase implement various
API calls on the Nova cluster having to do with creating and deleting VMs.
Each sub-class will have a corresponding PendingAction. These pending
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

__author__ = "Eugene Shih"

# system imports
import json
import random
import sys
import time
import os
import logging

# import kong modules
import kong.nova
from kong.common import ssh
import kong.exceptions

# local imports
import test_case
import state
import pending_action
from basherexceptions import *
import utils.env

# borrowed from openstack-integration-tests/kong
def _assert_server_entity(server, connection):

    actual_keys = set(server.keys())
    expected_keys = set((
            'id',
            'name',
            'hostId',
            'status',
            'metadata',
            'addresses',
            'links',
            'progress',
            'image',
            'flavor',
            'created',
            'updated',
            'accessIPv4',
            'accessIPv6',

            #KNOWN-ISSUE lp804093
            'uuid',
            ))
    assert(expected_keys <= actual_keys)

    server_id = str(server['id'])
    host = utils.env.NOVA_HOST
    port = utils.env.NOVA_PORT
    api_url = '%s:%s' % (host, port)
    base_url = os.path.join(api_url, utils.env.NOVA_VERSION)

    self_link = 'http://' + os.path.join(base_url,
                                         connection.project_id,
                                         'servers', server_id)
    bookmark_link = 'http://' + os.path.join(api_url,
                                             connection.project_id,
                                             'servers', server_id)

    expected_links = [
        {
            'rel': 'self',
            'href': self_link,
        },
        {
            'rel': 'bookmark',
            'href': bookmark_link,
        },
        ]

    assert(server['links'] == expected_links)


class TestCreateVM(test_case.TestCase):
    """Create a virtual machine in the Nova cluster."""
    _vm_id = 0

    def run(self, connection, state, *pargs, **kwargs):
        """
        Send an HTTP POST request to the nova cluster to build a
        server. Update the state variable to track state of new server
        and set to PENDING state.

        `connection` : object returned by kong.nova.API
        `state`      : `State` object describing our view of state of cluster
        `pargs`      : positional arguments
        `kwargs`     : keyword arguments, which include:
                       `key_name`  : name of keypair
                       `timeout`   : how long to wait before issuing Exception
                       `image_ref` : index to image types availablexs
                       `flavor_ref`: index to flavor types available
                                     (default = 1, which is tiny)
        """

        # restrict number of instances we can launch
        if len(state.get_machines()) >= state.get_max_machines():
            self._logger.debug("maximum number of machines created: %d" % 
                               state.get_max_machines())
            return None

        _key_name = kwargs.get('key_name', '')
        _timeout = int(kwargs.get('timeout', 60))
        _image_ref = int(kwargs.get('image_ref', 2))
        _flavor_ref = int(kwargs.get('flavor_ref', 1))

        expected_server = {
            'name': 'server' + str(TestCreateVM._vm_id),
            'metadata': {
                'key1': 'value1',
                'key2': 'value2',
                },
            'imageRef': _image_ref,
            'flavorRef': _flavor_ref,
            'adminPass': 'testpwd',
            'key_name' : _key_name
            }
        TestCreateVM._vm_id = TestCreateVM._vm_id + 1

        post_body = json.dumps({'server': expected_server})
        (response, body) = connection.request('POST',
                                              '/servers',
                                              body=post_body)
        if (response.status != 202):
            self._logger.error("response: %s" % response)
            self._logger.error("body: %s" % body)
            raise Exception

        _body = json.loads(body)
        assert(_body.keys() == ['server'])
        created_server = _body['server']

        self._logger.info('setting machine %s to BUILD' %
                          created_server['id'])
        state.set_machine_state(created_server['id'],
                                (created_server, 'BUILD'))

        return VerifyCreateVM(connection,
                              state,
                              created_server,
                              expected_server,
                              timeout=_timeout)

class VerifyCreateVM(pending_action.PendingAction):
    """Verify that VM was built and is running"""
    def __init__(self, connection,
                 state,
                 created_server,
                 expected_server,
                 timeout=600):
        super(VerifyCreateVM, self).__init__(connection,
                                             state,
                                             created_server,
                                             timeout)
        self._expected = expected_server

    def retry(self):
        """
        Check to see that the server was created and is running.
        Update local view of state to indicate that it is running.
        """
        # don't run create verification
        # if target machine has been deleted or is going to be deleted
        if (self._target['id'] not in self._state.get_machines().keys() or
            self._state.get_machines()[self._target['id']][1] == 'TERMINATING'):
            self._logger.info('machine %s is deleted or TERMINATING' %
                               self._target['id'])
            return True

        time_diff = time.time() - self._start_time
        if time_diff > self._timeout:
            self._logger.error('%d exceeded launch server timeout of %d' %
                               (time_diff, self._timeout))
            raise TimeoutException

        admin_pass = self._target['adminPass']
        _assert_server_entity(self._target, self._connection)
        if ((self._expected['name'] != self._target['name']) or
            (self._expected['metadata'] != self._target['metadata']) or
            (self._expected['adminPass'] != admin_pass) or
            (self._expected['key_name'] != self._target['key_name'])):
            self._logger.error('expected: %s %s %s %s' %
                               (self._expected['name'],
                                self._expected['metadata'],
                                self._expected['adminPass'],
                                self._expected['key_name']))
            self._logger.error('returned: %s %s %s %s' %
                               (self._target['name'],
                                self._target['metadata'],
                                adminPass,
                                self._expected['key_name']))
            raise Exception

        if self._check_for_status('ACTIVE') != 'ACTIVE':
            return False

        server = self._connection.get_server(self._target['id'])

        # Find private IP of server
        # try:
        #     (_, network) = server['addresses'].popitem()
        #     ip = network[0]['addr']
        # except KeyError:
        #     self._logger.error('could not get ip address for machine %s' %
        #                        self._target['id'])
        #     raise Exception

        # client = ssh.Client(ip, 'root', admin_pass, 60)
        # if not client.test_connection_auth():
        #     self._logger.error('machine: %s, ip: %s, pwd: %s' %
        #                        (self._target['id'], ip, admin_pass))
        #     raise Exception

        self._logger.info('machine %s: BUILD -> ACTIVE [%.1f secs elapsed]' %
                          (self._target['id'], time.time() - self._start_time))
        self._state.set_machine_state(self._target['id'],
                                      (self._target, 'ACTIVE'))
        return True

class TestKillActiveVM(test_case.TestCase):
    """Class to destroy a random ACTIVE server."""
    def run(self, connection, state, *pargs, **kwargs):
        """
        Send an HTTP POST request to the nova cluster to destroy
        a random ACTIVE server. Update `state` to indicate TERMINATING.

        `connection` : object returned by kong.nova.API
        `state`      : `State` object describing our view of state of cluster
        `pargs`      : positional arguments
        `kwargs`     : keyword arguments, which include:
                       `timeout` : how long to wait before issuing Exception
        """
        # check for active machines
        vms = state.get_machines()
        active_vms = [v for k, v in vms.iteritems() if v and v[1] == 'ACTIVE']
        # no active vms, so return null
        if not active_vms:
            self._logger.info('no ACTIVE machines to delete')
            return

        _timeout = kwargs.get('timeout', 600)

        target = random.choice(active_vms)
        kill_target = target[0]
        connection.delete_server(kill_target['id'])
        self._logger.info('machine %s: ACTIVE -> TERMINATING' %
                          kill_target['id'])
        state.set_machine_state(kill_target['id'],
                                (kill_target, 'TERMINATING'))
        return VerifyKillActiveVM(connection, state, kill_target, timeout=_timeout)

class VerifyKillActiveVM(pending_action.PendingAction):
    """Verify that server was destroyed"""

    def retry(self):
        """
        Check to see that the server of interest is destroyed. Update
        state to indicate that server is destroyed by deleting it from local
        view of state.
        """

        # if target machine has been deleted from the state, then it was
        # already verified to be deleted
        if (not self._target['id'] in self._state.get_machines().keys()):
            return False

        time_diff = time.time() - self._start_time
        if time_diff > self._timeout:
            self._logger.error('server %s: %d exceeds terminate timeout of %d' %
                               (self._target['id'], time_diff, self._timeout))
            raise TimeoutException

        try:
            url = '/servers/%s' % self._target['id']
            self._connection.poll_request_status('GET', url, 404, timeout=0)
        except kong.exceptions.TimeoutException:
            return False

        # if we get a 404 response, is the machine really gone?
        self._logger.info('machine %s: DELETED [%.1f secs elapsed]' %
                          (self._target['id'], time.time() - self._start_time))
        self._state.set_machine_state(self._target['id'], None)

        return True

class TestKillAnyVM(test_case.TestCase):
    """Class to destroy a random server regardless of state."""

    def run(self, connection, state, *pargs, **kwargs):
        """
        Send an HTTP POST request to the nova cluster to destroy
        a random server. Update state to TERMINATING.

        `connection` : object returned by kong.nova.API
        `state`      : `State` object describing our view of state of cluster
        `pargs`      : positional arguments
        `kwargs`     : keyword arguments, which include:
                       `timeout` : how long to wait before issuing Exception
        """

        vms = state.get_machines()
        # no vms, so return null
        if not vms:
            self._logger.info('no active machines to delete')
            return

        _timeout = kwargs.get('timeout', 60)

        target = random.choice(vms)
        kill_target = target[0]

        connection.delete_server(kill_target['id'])
        self._state.set_machine_state(kill_target['id'],
                                      (kill_target, 'TERMINATING'))
        # verify object will do the same thing as the active VM
        return VerifyKillAnyVM(connection, state, kill_target, timeout=_timeout)

VerifyKillAnyVM = VerifyKillActiveVM

class TestUpdateVMName(test_case.TestCase):
    """Class to change the name of the active server"""
    def run(self, connection, state, *pargs, **kwargs):
        """
        Issue HTTP POST request to change the name of active server.
        Update state of server to reflect name changing.

        `connection` : object returned by kong.nova.API
        `state`      : `State` object describing our view of state of cluster
        `pargs`      : positional arguments
        `kwargs`     : keyword arguments, which include:
                       `timeout`   : how long to wait before issuing Exception
        """

        # select one machine from active ones
        vms = state.get_machines()
        active_vms = [v for k, v in vms.iteritems() if v and v[1] == 'ACTIVE']
        # no active vms, so return null
        if not active_vms:
            self._logger.info('no active machines to update')
            return

        _timeout = kwargs.get('timeout', 600)

        target = random.choice(active_vms)
        update_target = target[0]

        # Update name by appending '_updated' to the name
        new_server = {'name': update_target['name'] + '_updated'}
        put_body = json.dumps({
                'server': new_server,
                })
        url = '/servers/%s' % update_target['id']
        (response, body) = connection.request('PUT',
                                              url,
                                              body=put_body)
        if (response.status != 200):
            self._logger.error("response: %s " % response)
            self._logger.error("body: %s " % body)
            raise Exception

        data = json.loads(body)
        assert(data.keys() == ['server'])
        _assert_server_entity(data['server'], connection)
        assert(update_target['name'] + '_updated' == data['server']['name'])

        self._logger.info('machine %s: ACTIVE -> UPDATING_NAME' %
                          data['server']['id'])
        state.set_machine_state(data['server']['id'],
                                (data['server'], 'UPDATING_NAME'))

        return VerifyUpdateVMName(connection,
                                  state,
                                  data['server'],
                                  timeout=_timeout)

class VerifyUpdateVMName(pending_action.PendingAction):
    """Check that VM has new name"""
    def retry(self):
        """
        Check that VM has new name. Update local view of `state` to RUNNING.
        """
        # don't run update verification
        # if target machine has been deleted or is going to be deleted
        if (not self._target['id'] in self._state.get_machines().keys() or
            self._state.get_machines()[self._target['id']][1] == 'TERMINATING'):
            return False

        if time.time() - self._start_time > self._timeout:
            raise TimeoutException

        response, body = self._connection.request('GET', '/servers/%s' %
                                                  self._target['id'])
        if (response.status != 200):
            self._logger.error("response: %s " % response)
            self._logger.error("body: %s " % body)
            raise Exception

        data = json.loads(body)
        if data.keys() != ['server']:
            self._logger.error(data.keys())
            raise Exception

        _assert_server_entity(data['server'], self._connection)
        if self._target['name'] != data['server']['name']:
            self._logger.error(self._target['name'] +
                               ' vs. ' +
                               data['server']['name'])
            raise Exception

        # log the update
        self._logger.info('machine %s: UPDATING_NAME -> ACTIVE' %
                          self._target['id'])
        self._state.set_machine_state(self._target['id'],
                                      (data['server'],
                                       'ACTIVE'))
        return True
