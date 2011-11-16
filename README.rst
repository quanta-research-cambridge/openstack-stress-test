OpenStack Basher Test System
============================

This is a framework for stress testing an OpenStack Nova cluster.

Clone a copy of openstack-stress-test::
  git clone https://github.com/quanta-research-cambridge/openstack-stress-test.git

Install Dependencies
--------------------

First install kong (openstack-integration-tests). Get a copy of it using::

  git clone https://github.com/openstack/openstack-integration-tests.git 

Switch to kong version that we developed with (TO DO: test latest version of kong)::

  git checkout 45333b375c533ba11a9048061a55253ab22efd49

Next, install kong dependencies. Kong depends on the following python
modules::

  nose
  paramiko

python-nose
python-paramiko

Update your PYTHONPATH
----------------------
Set PYTHONPATH to include kong and stress. You may want to edit your .bashrc (or
shell configuration) to modify the PYTHONPATH environment variable::

  export PYTHONPATH=[ROOT]/openstack-integration-tests:[ROOT]/openstack-stress-test:$PYTHONPATH

