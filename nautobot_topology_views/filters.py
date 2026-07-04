import django_filters
from django.db.models import Q
from nautobot.apps.filters import (
    MultiValueCharFilter,
    MultiValueMACAddressFilter,
    NautobotFilterSet,
    StatusFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.circuits.models import Circuit
from nautobot.dcim.filter_mixins import LocatableModelFilterSetMixin
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Location,
    Manufacturer,
    Platform,
    PowerFeed,
    PowerPanel,
    Rack,
)
from nautobot.extras.models import Role
from nautobot.tenancy.filter_mixins import TenancyModelFilterSetMixin

from nautobot_topology_views.models import (
    CircuitCoordinate,
    Coordinate,
    CoordinateGroup,
    PowerFeedCoordinate,
    PowerPanelCoordinate,
)


class DeviceFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin, LocatableModelFilterSetMixin):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        field_name='device_type__manufacturer',
        queryset=Manufacturer.objects.all(),
        label="Manufacturer (ID)",
    )
    manufacturer = django_filters.ModelMultipleChoiceFilter(
        field_name='device_type__manufacturer__name',
        queryset=Manufacturer.objects.all(),
        to_field_name='name',
        label="Manufacturer (name)",
    )
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label="Device type (ID)",
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        field_name="role_id",
        queryset=Role.objects.all(),
        label="Role (ID)",
    )
    platform_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        label="Platform (ID)",
    )
    location_id = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        field_name="location",
        lookup_expr="in",
        label="Location (ID)",
    )
    rack_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        field_name="rack_id",
        label="Rack (ID)",
    )
    # Device.status is a StatusField FK on Nautobot; filtering it with raw choice
    # strings raises ValidationError. StatusFilter matches by name or pk.
    status = StatusFilter()
    mac_address = MultiValueMACAddressFilter(
        field_name='interfaces__mac_address',
        label="MAC address",
    )
    serial = MultiValueCharFilter(
        lookup_expr='iexact'
    )
    console_ports = django_filters.BooleanFilter(
        method='_console_ports',
        label="Has console ports",
    )
    console_server_ports = django_filters.BooleanFilter(
        method='_console_server_ports',
        label="Has console server ports",
    )
    power_ports = django_filters.BooleanFilter(
        method='_power_ports',
        label="Has power ports",
    )
    power_outlets = django_filters.BooleanFilter(
        method='_power_outlets',
        label="Has power outlets",
    )
    interfaces = django_filters.BooleanFilter(
        method='_interfaces',
        label="Has interfaces",
    )
    pass_through_ports = django_filters.BooleanFilter(
        method='_pass_through_ports',
        label="Has pass-through ports",
    )
    has_primary_ip = django_filters.BooleanFilter(
        method='_has_primary_ip',
        label="Has a primary IP",
    )
    # (removed) has_oob_ip: core Device has no oob_ip field on Nautobot 3.x.
    virtual_chassis_member = django_filters.BooleanFilter(
        method='_virtual_chassis_member',
        label="Is a virtual chassis member",
    )

    class Meta:
        model = Device
        fields = ["id", "name", "asset_tag"]

    def search(self, queryset, name, value):
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        qs_filter = Q(name__icontains=value)
        return queryset.filter(qs_filter)

    def _console_ports(self, queryset, name, value):
        return queryset.exclude(consoleports__isnull=value)

    def _console_server_ports(self, queryset, name, value):
        return queryset.exclude(consoleserverports__isnull=value)

    def _power_ports(self, queryset, name, value):
        return queryset.exclude(powerports__isnull=value)

    def _power_outlets(self, queryset, name, value):
        return queryset.exclude(poweroutlets__isnull=value)

    def _interfaces(self, queryset, name, value):
        return queryset.exclude(interfaces__isnull=value)

    def _pass_through_ports(self, queryset, name, value):
        return queryset.exclude(
            frontports__isnull=value,
            rearports__isnull=value
        )

    def _has_primary_ip(self, queryset, name, value):
        params = Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)
        if value:
            return queryset.filter(params)
        return queryset.exclude(params)

    def _virtual_chassis_member(self, queryset, name, value):
        return queryset.exclude(virtual_chassis__isnull=value)

class CircuitCoordinateFilterSet(NautobotFilterSet):
    group = django_filters.ModelMultipleChoiceFilter(
        queryset = CoordinateGroup.objects.all(),
    )

    device = django_filters.ModelMultipleChoiceFilter(
        queryset = Circuit.objects.all(),
    )

    class Meta:
        model = CircuitCoordinate
        fields = ['id', 'group', 'device', 'x', 'y']

    def search(self, queryset, name, value):
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(group__name__icontains=value) |
            Q(device__name__icontains=value)
        )

class PowerPanelCoordinateFilterSet(NautobotFilterSet):
    group = django_filters.ModelMultipleChoiceFilter(
        queryset = CoordinateGroup.objects.all(),
    )

    device = django_filters.ModelMultipleChoiceFilter(
        queryset = PowerPanel.objects.all(),
    )

    class Meta:
        model = PowerPanelCoordinate
        fields = ['id', 'group', 'device', 'x', 'y']

    def search(self, queryset, name, value):
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(group__name__icontains=value) |
            Q(device__name__icontains=value)
        )

class PowerFeedCoordinateFilterSet(NautobotFilterSet):
    group = django_filters.ModelMultipleChoiceFilter(
        queryset = CoordinateGroup.objects.all(),
    )

    device = django_filters.ModelMultipleChoiceFilter(
        queryset = PowerFeed.objects.all(),
    )

    class Meta:
        model = PowerFeedCoordinate
        fields = ['id', 'group', 'device', 'x', 'y']

    def search(self, queryset, name, value):
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(group__name__icontains=value) |
            Q(device__name__icontains=value)
        )

class CoordinateFilterSet(NautobotFilterSet):
    group = django_filters.ModelMultipleChoiceFilter(
        queryset = CoordinateGroup.objects.all(),
    )

    device = django_filters.ModelMultipleChoiceFilter(
        queryset = Device.objects.all(),
    )

    class Meta:
        model = Coordinate
        fields = ['id', 'group', 'device', 'x', 'y']

    def search(self, queryset, name, value):
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(group__name__icontains=value) |
            Q(device__name__icontains=value)
        )


class CoordinateGroupFilterSet(NautobotFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = CoordinateGroup
        fields = ['id', 'name']

    def search(self, queryset, name, value):
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value))
