# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
# Copyright 2013 Big Switch Networks
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Methods and interface objects used to interact with external APIs.

API method calls return objects that are in many cases objects with
attributes that are direct maps to the data returned from the API http call.
Unfortunately, these objects are also often constructed dynamically, making
it difficult to know what data is available from the API object.  Because of
this, all API calls should wrap their returned object in one defined here,
using only explicitly defined attributes and/or methods.

In other words, Horizon developers not working on cloud.api
shouldn't need to understand the finer details of APIs for
Keystone/Nova/Glance/Swift et. al.
"""
from cloud.api import base
from cloud.api import ceilometer
from cloud.api import cinder
#from cloud.api import fwaas
from cloud.api import glance
#from cloud.api import heat
from cloud.api import keystone
#from cloud.api import lbaas
from cloud.api import network
from cloud.api import neutron
from cloud.api import nova
#from cloud.api import sahara
#from cloud.api import swift
#from cloud.api import trove
#from cloud.api import vpn


__all__ = [
    "base",
    "cinder",
    "fwaas",
    "glance",
    "heat",
    "keystone",
    "lbaas",
    "network",
    "neutron",
    "nova",
    "swift",
    "ceilometer",
    "trove",
    "vpn",
    "sahara",
]
