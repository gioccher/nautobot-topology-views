from nautobot.dcim.models import Device
from nautobot.extras.models import Role
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from nautobot.apps.api import NautobotModelSerializer

from nautobot_topology_views.models import RoleImage, IndividualOptions, CoordinateGroup, Coordinate, CircuitCoordinate, PowerPanelCoordinate, PowerFeedCoordinate, VirtualMachineCoordinate


class TopologyDummySerializer(ModelSerializer):
    class Meta:
        model = Device
        fields = ("id", "name")


class RoleImageSerializer(ModelSerializer):
    role = SerializerMethodField()

    def get_role(self, obj):
        return {"slug": obj.role_data.slug, "name": obj.role_data.name}

    class Meta:
        model = RoleImage
        fields = ("role", "image")


class DeviceRoleSerializer(ModelSerializer):
    class Meta:
        model = Role
        fields = ("name", "color", "description")

class CoordinateGroupSerializer(NautobotModelSerializer):
    class Meta:
        model = CoordinateGroup
        fields = ("name", "description")

class CoordinateSerializer(NautobotModelSerializer):
    class Meta:
        model = Coordinate
        fields = ("x", "y")

class CircuitCoordinateSerializer(NautobotModelSerializer):
    class Meta:
        model = CircuitCoordinate
        fields = ("x", "y")

class PowerPanelCoordinateSerializer(NautobotModelSerializer):
    class Meta:
        model = PowerPanelCoordinate
        fields = ("x", "y")

class PowerFeedCoordinateSerializer(NautobotModelSerializer):
    class Meta:
        model = PowerFeedCoordinate
        fields = ("x", "y")

class VirtualMachineCoordinateSerializer(NautobotModelSerializer):
    class Meta:
        model = VirtualMachineCoordinate
        fields = ("x", "y")

class IndividualOptionsSerializer(NautobotModelSerializer):
    class Meta:
        model = IndividualOptions
        fields = ("ignore_cable_type", "save_coords", "show_unconnected", "show_cables", "show_logical_connections",
            "show_single_cable_logical_conns", "show_neighbors", "show_circuit", "show_power", "show_wireless", "show_virtual_machines", "group_sites",
            "group_locations", "group_racks", "group_virtualchassis", "draw_default_layout", "straight_cables",
            "draw_termination_labels", "draw_cable_labels", "grid_size", "node_label_items")
