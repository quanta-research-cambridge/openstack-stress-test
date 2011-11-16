OpenStack Basher Test System
============================

This is a framework for stress testing a OpenStack Nova cluster.

QuickStart
----------

Get kong::

  git clone https://github.com/openstack/openstack-integration-tests.git 
  git checkout 45333b375c533ba11a9048061a55253ab22efd49

Install Dependencies
--------------------

kong / openstack-integration-tests

Get a copy of kong::

  git clone https://github.com/openstack/openstack-integration-tests.git 

Switch to kong version that we developed with (TO DO: test latest version of kong)::

  git checkout 45333b375c533ba11a9048061a55253ab22efd49

Set PYTHONPATH to include kong. You may want to edit your .bashrc (or
shell configuration) to modify the PYTHONPATH environment variable::

  export PYTHONPATH=$PWD/openstack-integration-tests:$PYTHONPATH

