#-*-coding-utf-8-*-

# Author Yang

from datetime import datetime
import logging

from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
#update 2016.06.02
from rest_framework.decorators import api_view, permission_classes
#update end
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import check_password

from biz.account.settings import QUOTA_ITEM, NotificationLevel
from biz.policy_neutron.models import Policy_Neutron 
from biz.policy_neutron.serializer import Policy_NeutronSerializer
from biz.policy_neutron.utils import * 
from biz.idc.models import DataCenter
from biz.common.pagination import PagePagination
from biz.common.decorators import require_POST, require_GET
#update 2016.06.02
from biz.common.views import IsSystemUser, IsSafetyUser, IsAuditUser
#update end
from biz.common.utils import retrieve_params, fail
from biz.workflow.models import Step
from cloud.tasks import (link_user_to_dc_task, send_notifications,
                         send_notifications_by_data_center)
from frontend.forms import CloudUserCreateFormWithoutCapatcha

LOG = logging.getLogger(__name__)

from openstack_auth.openstack.common import policy
import traceback

from oslo_serialization import jsonutils
import cloud.api.keystone as keystone
from django.contrib.auth.models import User
from biz.idc.models import UserDataCenter, DataCenter
from cloud.cloud_utils import create_rc_by_dc
#import shutil

str_format = ['(',')','rule:','role:']
role_format = ['is_admin:True','admin_api']

def format_role(role):
    for sf in str_format:
	role = role.replace(sf,'')
    for rf in role_format:
	role = role.replace(rf,'admin')
    role = role.replace(' or ',' , ')
    role = role.split(" , ")
    if "admin_or_owner" in role:
	LOG.info(role)
    return role

class Policy_NeutronList(generics.ListAPIView):
    #update 2016.06.02
    permission_classes = (IsSafetyUser,)
    #update end
    LOG.info("--------- I am policy_neutron list in Policy_NeutronList ----------")
    queryset = Policy_Neutron.objects.all().filter(deleted=False)
    LOG.info("--------- Queryset is --------------" + str(queryset)) 
    serializer = Policy_NeutronSerializer(queryset, many=True)
    def list(self, request):
	#queryset = Policy_Neutron.objects.all()
        LOG.info("******** list method **********")
	mypolicy = policy.Enforcer()
        LOG.info("********* mypolicy is ***********" + str(mypolicy))
        mypolicy._load_policy_file('/etc/neutron/policy.json', False)
        LOG.info("**************")
        out = {}
        LOG.info(mypolicy.rules)
        for key,value in mypolicy.rules.items():
            if isinstance(value, policy.TrueCheck):
                out[key] = ''
            else:
                out[key] = str(value)

	#------------------------- get role -------------------------------------
    	#rc = create_rc_by_dc(DataCenter.objects.all()[0])
    	#roles = []
    	#for role in keystone.role_list(rc):
        #    roles.append({"role":role.name})
	
	#sorted_rule = sorted(out.iteritems(), key=lambda d:d[0])
	result = []
	action = ['create_subnet', 
                "get_subnet",
                "update_subnet",
                "delete_subnet",
                "create_network",
                "get_network",
                "update_network",
                "delete_network"
		]
	#-------------------------- return policy-------------------------------------
	for key in out:
	    if key in action:
		if out[key] == '':
			out[key] = ['all']
		else:
	    		out[key] = format_role(out[key])
		result.append({'action':key,'role':out[key]})
	    #role_data = User.objects.all().filter(username= 'evercloud')
	    #LOG.info(role_data)
	    #role_udc = UserDataCenter.objects.all().filter(user=role_data[0].id)
	    #role_udc = UserDataCenter.objects.get(user=role_data[0])
	    #LOG.info("-----------UserDataCenter---------------")
	    #LOG.info(role_data.is_superuser)
	    #LOG.info(DataCenter.objects.all())
	    #LOG.info(type(UserDataCenter.objects.all().filter(user=role_data[0])[0].user))
	    #LOG.info(role_udc.keystone_user)
	    #LOG.info(role_udc.keystone_password)
	    #LOG.info(role_udc.tenant_name)
	    #LOG.info(role_udc.tenant_uuid)	
	    #LOG.info(role_udc.data_center.auth_url)
	    #LOG.info(str(request.session))
	    #LOG.info(UDC)
     	#    rc = create_rc_by_dc(DataCenter.objects.all()[0])
	#    roles = keystone.role_list(rc)
	#    for name in roles:
#		LOG.info(name.name)
	#LOG.info(rc)
	#LOG.info(request.data.get("auth_url"))
	#try:
	#    LOG.info(keystone.role_list(request))
	return Response(result)


@require_POST
def create_policy_neutron(request):
    """ 
    LOG.info("--------------------  init model -----------------------")
    mypolicy = policy.Enforcer()
    mypolicy._load_policy_file('/etc/nova/policy.json', False)
    out = {}
    #LOG.info(mypolicy.rules)
    for key,value in mypolicy.rules.items():
        if isinstance(value, policy.TrueCheck):
            out[key] = ''
        else:
            out[key] = str(value)
    LOG.info("------------------- get out -----------------------------")	
    #try:
    for key in out:
	try:
	    serializer = Policy_NeutronSerializer(data={'action':[key],'role':[out[key]]})
            if serializer.is_valid():
                ins = serializer.save(action=key)
		LOG.info(ins)
            else:
                return Response({"success": False, "msg": _('Policy_Neutron data is not valid!'),
                             'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
	    traceback.print_exc()
            LOG.info("Failed to create flavor, msg:[%s]" % e)
            return Response({"success": False, "msg": _('Failed to create policy_neutron for unknown reason.')})
    queryset = Policy_Neutron.objects.all()
    LOG.info(queryset)
    return Response({'success': True, "msg": _('Policy_Neutron is created successfully!')},
                            status=status.HTTP_201_CREATED)
"""
    return Response({'success': True, "msg": _('Policy_Neutron is created successfully!')},
                            status=status.HTTP_201_CREATED)

class role_list_view(generics.ListAPIView):
    #role_data = User.objects.all().filter(username= 'evercloud')
    #------------------------- get current role -----------------------
    """
    all_check = False
    roles = []
    policy_role = request.DATA.get("role")
    policy_role = split(' , ')
    if "all" in policy_role:
        all_check = True
    if "admin_or_owner" in policy_role:
	roles.append({"role":owner, "check":1})
	roles.append({"role":admin, "check":1})
    for role in keystone.role_list(rc):
	if (not all_check) and (role in policy_role):
	    roles.append({"role":role.name,"check":1})
	else:
	    roles.append({"role":role.name,"check":0})
    """
    def list(self, request):
        rc = create_rc_by_dc(DataCenter.objects.all()[0])
        roles = []
        for role in keystone.role_list(rc):
 	    roles.append({"role":role.name})
        roles.append({"role":"admin_or_owner"})
        #keystone.role_list(rc)
        #LOG.info(roles)
        return Response(roles)



@api_view(["POST"])
def delete_policy_neutrons(request):
    ids = request.data.getlist('ids[]')
    Policy_Neutron.objects.filter(pk__in=ids).delete()
    return Response({'success': True, "msg": _('Policy_Neutrons have been deleted!')}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def update_policy_neutron(request):
    try:
        #shutil.copy('/etc/nova/test_nova_policy.json',  '/etc/nova/new.json')
	LOG.info("==================== action =====================")
	#action = request.data['action']
	LOG.info(request.data.get("action"))
	LOG.info(request.data['roles'])
	
	mypolicy = policy.Enforcer()
        mypolicy._load_policy_file('/etc/neutron/policy.json', False)
        out = {}
        for key,value in mypolicy.rules.items():
            if isinstance(value, policy.TrueCheck):
                out[key] = ''
            else:
                out[key] = str(value)
	if request.data['roles'] == "all":
		new_roles = ""
	elif request.data['roles'] =='':
		return Response(
            {'success': False, "msg": _('No role is selected!')},
            status=status.HTTP_201_CREATED)

	else:
		new_roles = request.data['roles'].replace(',',' or ')   
	#new_roles = new_roles.replace('owner', 'project_id:%(project_id)s')
	#new_roles = new_roles.replace('owner', 'admin_or_owner')
	#LOG.info(new_roles) 
        for key in out:
            if key == request.data['action']:
                out[key] = new_roles
		#LOG.info(out[key])
	policy_json = jsonutils.dumps(out)
	policy_json = policy_json.replace(',',',\n')	
	f = open('/etc/neutron/policy.json', 'w')
	try:
	    f.write(policy_json)
	except:
	    write_fail_msg = 'Failed to write policy information to file!'
	    f.close()
	    return Response({"success": False, "msg": _(write_fail_msg)})
	f.close()
        return Response(
            {'success': True, "msg": _('Policy_Neutron is updated successfully!')},
            status=status.HTTP_201_CREATED)

    except Exception as e:
        LOG.error("Failed to update policy_neutron, msg:[%s]" % e)
        return Response({"success": False, "msg": _(
            'Failed to update policy_neutron for unknown reason.')})


@require_GET
def is_policy_neutronname_unique(request):
    policy_neutronname = request.GET['policy_neutronname']
    LOG.info("policy_neutronname is" + str(policy_neutronname))
    return Response(not Policy_Neutron.objects.filter(policy_neutronname=policy_neutronname).exists())
