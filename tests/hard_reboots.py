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
import datetime
import uuid
import sys

# import kong modules
# Make sure you add openstack-integration-tests to your PYTHONPATH
import kong.nova

# local imports
from stress.test_case import *
from stress.test_servers import *
from stress.test_server_actions import *
from stress.basher import BasherChoice
from stress.driver import *
from stress.utils.env import *
from stress.utils.nova import *

key_name = str(uuid.uuid1())

choice_spec = [
    BasherChoice(TestCreateVM(), 50,
                 kargs={'timeout' : '600',
                        'key_name' : key_name}),
    BasherChoice(TestRebootVM(), 50,
                 kargs={'type' : 'HARD'}),
]

nova = kong.nova.API(NOVA_HOST,
                     NOVA_PORT,
                     NOVA_VERSION,
                     NOVA_USERNAME,
                     NOVA_API_KEY,
                     NOVA_PROJECT)

create_keypair(nova, key_name)

bash_openstack(nova,
               choice_spec,
               duration=datetime.timedelta(seconds=180),
               sleep_time=10000, # in milliseconds
               seed=int(time.time()),
               test_name="hard reboots",
               max_vms=32)

cleanup_keypair(nova, key_name)
