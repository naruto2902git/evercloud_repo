#coding=utf-8

import logging

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import api_view
from rest_framework.response import Response

from biz.account.models import Operation
from biz.idc.models import DataCenter, UserDataCenter
from biz.floating.models import Floating
from biz.floating.serializer import FloatingSerializer
from biz.floating.settings import FLOATING_STATUS_DICT, FLOATING_ALLOCATE, FLOATING_APPLYING
from biz.floating.utils import floating_action
from biz.account.utils import check_quota
from biz.billing.models import Order
from biz.workflow.settings import ResourceType
from biz.workflow.models import Workflow, FlowInstance
from cloud.cloud_utils import create_rc_by_dc
from cloud.tasks import allocate_floating_task
from cloud.api import keystone

from biz.instance.models import Instance
from biz.lbaas.models import BalancerPool

LOG = logging.getLogger(__name__)

@api_view(["GET"])
def list_view(request):

    udc_id = request.session["UDC_ID"]
    system = False
    security = False
    audit = False
    member = False
    UDC = UserDataCenter.objects.get(pk=udc_id)
    LOG.info(UDC)
    LOG.info("4")
    keystone_user_id = UDC.keystone_user_id
    LOG.info("4")
    tenant_uuid = UDC.tenant_uuid
    LOG.info("4")
    rc = create_rc_by_dc(DataCenter.objects.all()[0])
    LOG.info("4")
    LOG.info(str(keystone_user_id))
    LOG.info(str(tenant_uuid))
    user_roles = keystone.roles_for_user(rc, keystone_user_id, tenant_uuid)
    LOG.info("4")
    for user_role in user_roles:
        LOG.info("5")
        LOG.info(user_role.name)
        if user_role.name == "system":
            LOG.info("5")
            system = True
            break
        if user_role.name == "security":
            security = True
            break
        if user_role.name == "audit":
            audit = True
            break

        if not system and not security and not audit:
            member = True
    """
    if system:
        floatings = Floating.objects.filter(deleted=False)
        serializer = FloatingSerializer(floatings, many=True)
        return Response(serializer.data)
    """
    floatings = Floating.objects.filter(deleted=False)
    serializer = FloatingSerializer(floatings, many=True)
    return Response(serializer.data)
    floatings = Floating.objects.filter(user=request.user,
                                        user_data_center=request.session["UDC_ID"],
                                        deleted=False)
    serializer = FloatingSerializer(floatings, many=True)
    return Response(serializer.data)


@check_quota(["floating_ip"])
@api_view(["POST"])
def create_view(request):
    floating = Floating.objects.create(
        ip="N/A",
        status=FLOATING_ALLOCATE,
        bandwidth=int(request.POST["bandwidth"]),
        user=request.user,
        user_data_center=UserDataCenter.objects.get(pk=request.session["UDC_ID"])
    )

    pay_type = request.data['pay_type']
    pay_num = int(request.data['pay_num'])

    Operation.log(floating, obj_name=floating.ip, action='allocate', result=1)

    workflow = Workflow.get_default(ResourceType.FLOATING)

    if settings.SITE_CONFIG['WORKFLOW_ENABLED'] and workflow:

        floating.status = FLOATING_APPLYING
        floating.save()

        FlowInstance.create(floating, request.user, workflow, None)
        msg = _("Your application for %(bandwidth)d Mbps floating ip is successful, "
                "please waiting for approval result!") % {'bandwidth': floating.bandwidth}
    else:
        msg = _("Your operation is successful, please wait for allocation.")
        allocate_floating_task.delay(floating)
        Order.for_floating(floating, pay_type, pay_num)

    return Response({"OPERATION_STATUS": 1, 'msg': msg})


@api_view(["POST"])
def floating_action_view(request):
    data = floating_action(request.user, request.DATA)
    return Response(data)


@api_view(["GET"])
def floating_status_view(request):
    return Response(FLOATING_STATUS_DICT)


@api_view(['GET'])
def floating_ip_target_list_view(request):

    instance_set = Instance.objects.filter(
        deleted=False,  user=request.user,
        user_data_center=request.session["UDC_ID"])
    pool_set = BalancerPool.objects.filter(
        vip__public_address=None, deleted=False, user=request.user,
        user_data_center=request.session["UDC_ID"]).exclude(vip=None)

    resources = []
    instance_floatings = Floating.objects.filter(
        deleted=False, resource_type="INSTANCE")
    ins_ids = [f.resource for f in instance_floatings]
    for instance in instance_set: 
        if instance.id not in ins_ids:
            resources.append({
                "name": "server:" + instance.name,
                "id": instance.id,
                "resource_type": "INSTANCE"})

    for pool in pool_set:
        resources.append({"name": "lb-vip:" + pool.name,
                          "id": pool.id,
                          "resource_type": "LOADBALANCER"})

    return Response(resources)
