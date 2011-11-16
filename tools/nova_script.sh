#!/bin/bash

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

# assumes you've installed python-novaclient and source novarc
: ${NOVA_API_KEY:?"Need to set NOVA_API_KEY non-empty"}

nova keypair-add test > test.priv
nova keypair-list
chmod 600 test.priv
# nova keypair-delete test

# show flavors and images available
nova flavor-list
nova image-list

# create 1 vm, with name testserver
nova boot --flavor 1 --image 2 --key_name test testserver
ID=`nova list | grep testserver | awk '{print $2}'`
echo "ID: $ID"

# check security group
nova secgroup-list
nova secgroup-list-rules default

# sleep for 5 seconds
sleep 2
IP_ADDR=`nova floating-ip-create | grep "\." | awk '{print $2}'`
# get ip addresses
echo "IP_ADDR: $IP_ADDR"
nova floating-ip-list
nova add-floating-ip $ID $IP_ADDR

# ssh clean-up
ssh-keygen -f "$HOME/.ssh/known_hosts" -R $IP_ADDR
#ssh -q -o StrictHostKeyChecking=no -i test.priv ubuntu@$IP_ADDR

# cleanup
# nova remove-floating-ip $ID $IP_ADDR
# nova floating-ip-delete $IP_ADDR
# nova keypair-delete test
# nova delete testserver
