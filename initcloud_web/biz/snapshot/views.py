# -*- coding:utf8 -*-

# Author Yang

from datetime import datetime
import logging

from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import check_password

from biz.account.settings import QUOTA_ITEM, NotificationLevel
from biz.snapshot.models import Snapshot 
from biz.snapshot.serializer import SnapshotSerializer
from biz.snapshot.utils import * 
from biz.idc.models import UserDataCenter, DataCenter
from biz.common.pagination import PagePagination
from biz.common.decorators import require_POST, require_GET
from biz.common.utils import retrieve_params, fail
from biz.workflow.models import Step
from cloud.tasks import (link_user_to_dc_task, send_notifications,
                         send_notifications_by_data_center)
from frontend.forms import CloudUserCreateFormWithoutCapatcha
from cloud.api import nova
from cloud.api import glance
from cloud.api.glance import glanceclient
from cloud.cloud_utils import create_rc_by_udc, create_rc_by_dc
from biz.image.serializer import ImageSerializer
from biz.instance.models import Instance
from biz.image.models import Image

LOG = logging.getLogger(__name__)


def check_snapshotname(request):
    snap_name = request.data['snap_name']
    LOG.info(snap_name)
    LOG.info(Snapshot.objects.all().filter(snapshotname = snap_name).exists())
    return Snapshot.objects.all().filter(snapshotname = snap_name).exists()
    
class SnapshotList(generics.ListAPIView):
    LOG.info("--------- I am snapshot list in SnapshotList ----------")
    queryset = Snapshot.objects.all()
    LOG.info("--------- Queryset is --------------" + str(queryset)) 
    serializer_class = SnapshotSerializer
    def list(self, request):
        queryset = Snapshot.objects.all()
	serializer = SnapshotSerializer(queryset, many=True)
	return Response(serializer.data)



@require_POST
def create_instance_snapshot(request):
	    
    try:
	LOG.info(request.data)
	#id = request.data['id']
        if check_snapshotname(request):
            return Response({"success": False, "msg": _('Duplicated Snapshot name!Please enter another name')})
	snap_name = request.data['snap_name']
        instance_name = request.data['instance_name']
	instance_id = request.data['instance_id']
	#datacenter = DataCenter.get_default()
	udc_id = request.session["UDC_ID"]
	udc = UserDataCenter.objects.get(id = udc_id)
	rc = create_rc_by_udc(udc)
	snapshot = nova.snapshot_create(rc, instance_id, snap_name)
	serializer = SnapshotSerializer(data = {'snapshotname':snap_name,'snapshot_id':snapshot, 'snapshot_type':'instance', 'instance_id':instance_id, 'snapshot_name': instance_name})
	if serializer.is_valid():
            serializer.save()
	ins = Instance.objects.all().get(id = request.data['id'])
	snap_name = "snapshot_" + snap_name
	ser = ImageSerializer(ins.image)
	ser_data = ser.data
	del ser_data['id']
	image_ser = ImageSerializer(data = ser_data,  context = {"request":request})
	if image_ser.is_valid():
	    image = image_ser.save()
	image.name = snap_name
	image.uuid = snapshot
	image.save()
        return Response({'success': True, "msg": _('Snapshot is created successfully!')},
                            status=status.HTTP_201_CREATED)
    except Exception as e:
        LOG.error("Failed to create flavor, msg:[%s]" % e)
        return Response({"success": False, "msg": _('Failed to create snapshot for unknown reason.')})



@api_view(["POST"])
def boot_snapshot(request):
    LOG.info(request.data)
    
    return Response({'success': True, "msg": _('Snapshot is created successfully!')})

@api_view(["POST"])
def delete_snapshots(request):
    LOG.info("request data is ids")
    ids = request.data.getlist('ids[]')
    datacenter = DataCenter.get_default()
    rc = create_rc_by_dc(datacenter)
    LOG.info(settings.GLANCE_ENDPOINT)
    url = settings.GLANCE_ENDPOINT
    try:
        client = glance.glanceclient(rc,url)
	for snapshot in Snapshot.objects.filter(pk__in=ids):
	    image_id = snapshot.snapshot_id
	    LOG.info(image_id)
            try:
     	        client.images.delete(image_id)
            except Exception as e:
                LOG.info(str(e)) 
                Snapshot.objects.filter(pk__in=ids).delete()
                LOG.info("dddd")
                Image.objects.filter(uuid = image_id).delete()
                LOG.info("dddd")
                continue
                return Response({'success': False, "msg": _('Snapshots have not been deleted!')}, status=status.HTTP_201_CREATED)
            LOG.info("dddd")
            Snapshot.objects.filter(pk__in=ids).delete()
            LOG.info("dddd")
	    Image.objects.filter(uuid = image_id).delete()
            LOG.info("dddd")
	return Response({'success': True, "msg": _('Snapshots have been deleted!')}, status=status.HTTP_201_CREATED)
    except:
	traceback.print_exc()
	return Response({'success': False, "msg": _('Failed to delete Snapshots!')})
	

@api_view(['POST'])
def update_snapshot(request):
    try:

        LOG.info(" **** requesta data is ***" + str(request.data))
        if check_snapshotname(request):
            return Response({"success": False, "msg": _('Duplicated Snapshot name!Please enter another name')})
        image_id = request.data.get('snapshot_id')
        name = request.data.get("snapshotname")
        pk = request.data.get("id")
        LOG.info("---- snapshot pk is --------" + str(pk))
        
        try:
            meta = {"name": name}
            LOG.info("1")
            udc_id = request.session["UDC_ID"]
            LOG.info("1")
            udc = UserDataCenter.objects.get(id = udc_id)
            LOG.info("1")
            rc = create_rc_by_udc(udc)
            LOG.info("1")
            url = settings.GLANCE_ENDPOINT
            glanceclient(rc, url).images.update(image_id, **meta)
            LOG.info("1")
        except Exception as e:
            LOG.info("**** error is ***" + str(e)) 
            if "Forbidden" in str(e):
                return Response(
                {'success': False, "msg": _('无权限修改此镜像!')},
            status=status.HTTP_201_CREATED)
            return Response(
            {'success': False, "msg": _('Snapshot updated failed!')},
            status=status.HTTP_201_CREATED)

        

        snapshot = Snapshot.objects.get(pk=pk)
        LOG.info("ddddddddddddd")
        LOG.info("request.data is" + str(request.data))
        snapshot.snapshotname = request.data['snapshotname']

        LOG.info("dddddddddddd")
        snapshot.save()
        #Operation.log(snapshot, snapshot.name, 'update', udc=snapshot.udc,
        #              user=request.user)

       
        return Response(
            {'success': True, "msg": _('Snapshot is updated successfully!')},
            status=status.HTTP_201_CREATED)

    except Exception as e:
        LOG.error("Failed to update snapshot, msg:[%s]" % e)
        return Response({"success": False, "msg": _(
            'Failed to update snapshot for unknown reason.')})


@require_GET
def is_snapshotname_unique(request):
    snapshotname = request.GET['snapshotname']
    LOG.info("snapshotname is" + str(snapshotname))
    return Response(not Snapshot.objects.filter(snapshotname=snapshotname).exists())
