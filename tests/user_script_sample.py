"""Sample stress test that creates a few virtual machines and then 
destroys them"""

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
from stress.basher import BasherChoice
from stress.driver import *
from stress.utils.env import *
from stress.utils.nova import *

key_name = str(uuid.uuid1())

choice_spec = [
    BasherChoice(TestCreateVM(), 50,
                 kargs={'timeout' : '300',
                        'key_name' : key_name}),
    BasherChoice(TestKillActiveVM(), 50)
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
               duration=datetime.timedelta(seconds=10),
               sleep_time=1000, # in milliseconds
               seed=None,
               test_name="simple create and delete",
               max_vms=10)

cleanup_keypair(nova, key_name)
