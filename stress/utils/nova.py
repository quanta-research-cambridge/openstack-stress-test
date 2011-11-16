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
import logging
import time
import os
import stat

# kong 
import kong.nova

def create_keypair(connection, name):
    # first check to see if name exists
    url = '/os-keypairs?fresh=%.2f' % time.time()
    (resp, body) = connection.request('GET', url)

    if (resp.status != 200):
        raise Exception
    data = json.loads(body)
    assert(data.keys() == ['keypairs'])
    keypair_list = data['keypairs']

    if keypair_list:
        matching_keypair = {}
        matching = [kp for kp in keypair_list if kp['keypair']['name'] == name]
        if len(matching) > 0:
            logging.error('keypair with same name (%s) as existing keypair' %
                          name)
            raise Exception

    url = '/os-keypairs'
    action = { 'name' : name }
    post_body = json.dumps({'keypair': action})
    (resp, body) = connection.request('POST',
                                      url,
                                      body=post_body)
    if (resp.status != 200):
        logging.error('response: %s' % resp)
        raise Exception

    data = json.loads(body)
    assert(data.keys() == ['keypair'])
    output = data['keypair']['private_key']

    # write to the private file
    filename = '%s.priv' % name
    fh = open(filename, 'w')
    fh.write(output)
    os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
    fh.close()

def cleanup_keypair(connection, name):
    # first check to see if name exists
    url = '/os-keypairs?fresh=%.2f' % time.time()
    (resp, body) = connection.request('GET', url)

    if (resp.status != 200):
        logging.error('response: %s' % resp)
        raise Exception
    data = json.loads(body)
    assert(data.keys() == ['keypairs'])
    keypair_list = data['keypairs']

    for kp in keypair_list:
        if kp['keypair']['name'] == name:
            url = '/os-keypairs/%s' % kp['keypair']['name']
            (resp, body) = connection.request('DELETE', url)
            if resp.status != 202:
                logging.error('response: %s' % resp)
                raise Exception
            logging.info('Deleting keypair %s' % kp['keypair']['name'])
            os.remove('%s.priv' % kp['keypair']['name'])
            break

def allocate_ip(connection):
    post_body = json.dumps({'floating_ip': ''})
    url = '/os-floating-ips'
    (resp, body) = connection.request('POST',
                                      url,
                                      body=post_body)

    if(resp.status != 200):
        logging.error('response: %s' % resp)
        raise Exception
    data = json.loads(body)
    logging.info('Allocated ip %s' % data['floating_ip']['ip'])
    return data['floating_ip']['ip']

def deallocate_ip(connection, floating_ip):
    # first check to see if name exists
    url = '/os-floating-ips?fresh=%.2f' % time.time()
    (resp, body) = connection.request('GET', url)

    if (resp.status != 200):
        logging.error('response: %s' % resp)
        raise Exception
    data = json.loads(body)
    assert(data.keys() == ['floating_ips'])
    ip_list = data['floating_ips']

    for ip in ip_list:
        if ip['ip'] == floating_ip:
            url = '/os-floating-ips/%s' % ip['id']
            (resp, body) = connection.request('DELETE', url)
            if resp.status != 202:
                logging.error('response: %s' % resp)
                raise Exception
            logging.info('Deleting floating ip %s' % floating_ip)
            break

def assign_ip(connection, server, floating_ip):
    pass
