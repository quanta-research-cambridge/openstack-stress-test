OpenStack Basher Test System
============================

This is a framework for stress testing a OpenStack Nova cluster.

Nova Cluster Installation
-------------------------

This test framework is designed to stress test a Nova cluster. Hence,
you must have a working Nova cluster. This particular framework
assumes your working Nova cluster understands Nova API 1.1.

Installation
------------

We will first create a sub-directory in your home directory:: 

  cd ~
  mkdir install
  cd install

Now, grab a copy of our stress test source::

  git clone https://github.com/quanta-research-cambridge/openstack-stress-test.git

Our code uses some of kong's libraries. To install kong /
openstack-integration-tests, we first get a copy of kong from their git
repository::

  git clone https://github.com/openstack/openstack-integration-tests.git 

Switch to the kong version that we developed with (TO DO: test latest version of kong)::

  cd openstack-integration-tests
  git checkout 45333b375c533ba11a9048061a55253ab22efd49
  cd ..

We need to set ``PYTHONPATH`` to include ``kong``. You may want to
edit your ``.bashrc`` (or shell configuration) to modify the
``PYTHONPATH`` environment variable. For now, simply execute the
following statement::

  export PYTHONPATH=$PWD/openstack-integration-tests:$PYTHONPATH

There are a few packages that kong depends on::

  paramiko

To install it on Ubuntu 11.04::

  sudo apt-get -y install python-paramiko

The following environment variables will also need to be defined::

  NOVA_API_KEY
  NOVA_USERNAME
  NOVA_PROJECT_ID
  NOVA_URL
  NOVA_VERSION

In our setup, we use ``nova-manage [project name] [zipfile name]`` to
generate a file that contains these values. The file is then sourced
before the test is executed.

Finally, you will need to provide the path to the private SSH key that
provides public key SSH access to the Nova controller. Set the environment
variable ``NOVA_SSH_KEY_PATH`` to this value. For example::

  export NOVA_SSH_KEY_PATH=/home/tester/.ssh/id_rsa.nova

where ``/home/tester/.ssh/id_rsa.nova`` is the private key that
corresponds to a public key stored in the ``/.ssh/authorized_keys``
file for the ``root`` user on the Nova controller.

Running the sample test
-----------------------

To test your installation, do the following::

  cd openstack-stress-test/stress
  python user_script_sample.py

This sample test tries to create a few VMs and kill a few VMs.


