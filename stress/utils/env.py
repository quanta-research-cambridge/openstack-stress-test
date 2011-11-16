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

import os

if not os.environ['NOVA_API_KEY']:
    print >> sys.stderr, "NOVA_API_KEY environment variable not set."
    raise Exception

# get the environment variables for credentials
nova_url=os.environ['NOVA_URL'].split('/')
NOVA_VERSION=nova_url[3]
NOVA_HOST=nova_url[2].split(':')[0]
NOVA_PORT=nova_url[2].split(':')[1]
NOVA_USERNAME=os.environ['NOVA_USERNAME']
NOVA_API_KEY=os.environ['NOVA_API_KEY']
NOVA_PROJECT=os.environ['NOVA_PROJECT_ID']
NOVA_URL=os.environ['NOVA_URL']
