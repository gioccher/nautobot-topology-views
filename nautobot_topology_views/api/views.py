from typing import Dict
import sys
import uuid

from nautobot.apps.api import NautobotModelViewSet
from nautobot.core.api.views import ModelViewSet as NautobotBaseViewSet

from nautobot.circuits.models import Circuit
from nautobot.dcim.models import Device, PowerFeed, PowerPanel
from nautobot.extras.models import Role
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet

from nautobot_topology_views.api.serializers import (
    RoleImageSerializer,
    TopologyDummySerializer,
    CoordinateGroupSerializer,
    CoordinateSerializer,
    CircuitCoordinateSerializer,
    PowerPanelCoordinateSerializer,
    PowerFeedCoordinateSerializer,
)
import nautobot_topology_views.models
from nautobot_topology_views.models import RoleImage, IndividualOptions, CoordinateGroup, Coordinate, CircuitCoordinate, PowerPanelCoordinate, PowerFeedCoordinate
from nautobot_topology_views.views import get_topology_data
from nautobot_topology_views.utils import get_image_from_url, export_data_to_xml, get_query_settings
from nautobot_topology_views.filters import DeviceFilterSet

class SaveCoordsViewSet(ReadOnlyModelViewSet):
    permission_required = 'nautobot_topology_views.change_coordinate'

    queryset = Device.objects.none()
    serializer_class = TopologyDummySerializer

    @action(detail=False, methods=["patch"])
    def save_coords(self, request):
        if not settings.PLUGINS_CONFIG["nautobot_topology_views"][
            "allow_coordinates_saving"
        ]:
            return Response({"status": "not allowed to save coords"}, status=500)

        device_id: str = request.data.get("node_id", None)
        x_coord = request.data.get("x", None)
        y_coord = request.data.get("y", None)
        group_id = request.data.get("group", "None")

        # Nautobot PKs are UUIDs (never numeric, and they may legitimately
        # start with 'c'/'p'/'f'). A bare id that parses as a UUID is a
        # device; the c/p/f prefixes mark circuit / power-panel / power-feed
        # nodes, whose remainder must itself parse as a UUID.
        def _resolve(node_id):
            try:
                return Device.objects.get(pk=uuid.UUID(node_id)), "Coordinate"
            except (ValueError, Device.DoesNotExist):
                pass
            prefixed = {
                "c": (Circuit, "CircuitCoordinate"),
                "p": (PowerPanel, "PowerPanelCoordinate"),
                "f": (PowerFeed, "PowerFeedCoordinate"),
            }
            model, prefixed_name = prefixed.get(node_id[:1], (None, None))
            if model is not None:
                try:
                    return model.objects.get(pk=uuid.UUID(node_id[1:])), prefixed_name
                except (ValueError, model.DoesNotExist):
                    pass
            return None, None

        actual_device, model_name = _resolve(device_id) if device_id else (None, None)

        if not actual_device:
            return Response({"status": "invalid node_id in body"}, status=400)

        model_class = getattr(nautobot_topology_views.models, model_name)

        if group_id is None or group_id == "default":
            group_id = model_class.get_or_create_default_group(group_id)
            if not group_id:
                return Response(
                    {"status": "Error while creating default group."}, status=500
                )

        try:
            if CoordinateGroup.objects.filter(pk=group_id):
                group = CoordinateGroup.objects.get(pk=group_id)
                # Update the existing row in place, or create one. Re-instantiating
                # with an existing pk (the previous approach) breaks on Nautobot's
                # PrimaryModel: the fresh instance carries created=None, so the
                # UPDATE writes NULL into a non-null column and every re-save of an
                # already-pinned node failed with a 500.
                coords = model_class.objects.filter(group=group, device=actual_device).first()
                if coords is None:
                    coords = model_class(group=group, device=actual_device, x=x_coord, y=y_coord)
                else:
                    coords.x = x_coord
                    coords.y = y_coord
                coords.save()
        except:
            return Response(
                {"status": "Coordinates could not be saved."}, status=500
            )

        return Response({"status": "saved coords"})

class ExportTopoToXML(ViewSet):
    queryset = Device.objects.none()
    serializer_class = TopologyDummySerializer

    def list(self, request):

        self.filterset = DeviceFilterSet
        self.queryset = Device.objects.filter().select_related(
            "device_type", "role"
        )
        self.queryset = self.filterset(request.GET, self.queryset).qs

        individualOptions, created = IndividualOptions.objects.get_or_create(
            user_id=request.user.id,
        )

        if request.GET:

            filter_id, ignore_cable_type, save_coords, show_unconnected, show_power, show_circuit, show_logical_connections, show_single_cable_logical_conns, show_cables, show_wireless, group_sites, group_locations, group_racks, group_virtualchassis, group, show_neighbors, straight_cables, draw_termination_labels, draw_cable_labels, grid_size, node_label_items = get_query_settings(request)

            if 'group' not in request.query_params:
                group_id = "default"
            else:
                group_id = request.query_params["group"]
            topo_data = get_topology_data(
                queryset=self.queryset,
                individualOptions=individualOptions,
                ignore_cable_type=ignore_cable_type,
                save_coords=save_coords,
                show_unconnected=show_unconnected,
                show_cables=show_cables,
                show_logical_connections=show_logical_connections,
                show_single_cable_logical_conns=show_single_cable_logical_conns,
                show_neighbors=show_neighbors,
                show_circuit=show_circuit,
                show_power=show_power,
                show_wireless=show_wireless,
                group_sites=group_sites,
                group_locations=group_locations,
                group_racks=group_racks,
                group_virtualchassis=group_virtualchassis,
                group_id=group_id,
                straight_cables=straight_cables,
                draw_termination_labels=draw_termination_labels,
                draw_cable_labels=draw_cable_labels,
                grid_size=grid_size,
                node_label_items=node_label_items,
            )
            xml_data = export_data_to_xml(topo_data).decode('utf-8').replace('\n', '&#xa;')

            return HttpResponse(xml_data, content_type="application/xml; charset=utf-8")
        else:
            return JsonResponse(
                {"status": "Missing or malformed request parameters"}, status=400
            )

class SaveRoleImageViewSet(ReadOnlyModelViewSet):
    queryset = Role.objects.none()
    serializer_class = RoleImageSerializer
    permission_required = (
        "dcim.add_role",
        "dcim.change_role",
    )

    @action(detail=False, methods=["post"])
    def save(self, request):
        if not isinstance(request.data, dict):
            return JsonResponse(
                {"status": "Missing or malformed request body"}, status=400
            )

        def _is_uuid(s):
            try:
                uuid.UUID(s)
                return True
            except (ValueError, AttributeError):
                return False

        device_roles = {
            k: v.removeprefix(settings.STATIC_URL)
            for k, v in request.data.items()
            if _is_uuid(k)}
        content_type_ids = {
            k[2:]: v.removeprefix(settings.STATIC_URL)
            for k, v in request.data.items()
            if k.startswith("ct") and k[2:].isnumeric()
        }

        roles: Dict[int, Role] = Role.objects.in_bulk(device_roles.keys())
        content_types: Dict[int, ContentType] = ContentType.objects.in_bulk(
            content_type_ids.keys()
        )

        if len(roles) != len(device_roles):
            difference = set(device_roles) - set(roles.keys())
            return JsonResponse(
                {"status": f"Got unknown device role ids: {difference}"},
                status=400,
            )

        if len(content_types) != len(content_type_ids):
            difference = set(content_type_ids) - set(content_types.keys())
            return JsonResponse(
                {"status": f"Got unknown content type ids: {difference}"},
                status=400,
            )

        if device_roles:
            device_role_ct = ContentType.objects.get_for_model(Role)

            for id, url in device_roles.items():
                RoleImage.objects.update_or_create(
                    defaults={"image": str(get_image_from_url(url))},
                    content_type_id=device_role_ct.pk,
                    object_id=id,
                )

        for content_type_id, url in content_type_ids.items():
            RoleImage.objects.update_or_create(
                defaults={"image": str(get_image_from_url(url))},
                content_type_id=content_type_id,
                object_id=None,
            )

        return JsonResponse({"status": "Ok"})

class CoordinateGroupViewSet(NautobotModelViewSet):
    queryset = CoordinateGroup.objects.all()
    serializer_class = CoordinateGroupSerializer

class CoordinateViewSet(NautobotModelViewSet):
    queryset = Coordinate.objects.all()
    serializer_class = CoordinateSerializer

class CircuitCoordinateViewSet(NautobotModelViewSet):
    queryset = CircuitCoordinate.objects.all()
    serializer_class = CircuitCoordinateSerializer

class PowerPanelCoordinateViewSet(NautobotModelViewSet):
    queryset = PowerPanelCoordinate.objects.all()
    serializer_class = PowerPanelCoordinateSerializer

class PowerFeedCoordinateViewSet(NautobotModelViewSet):
    queryset = PowerFeedCoordinate.objects.all()
    serializer_class = PowerFeedCoordinateSerializer
