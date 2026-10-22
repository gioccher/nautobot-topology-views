import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ChoiceFieldColumn

from nautobot_topology_views.models import (
    CircuitCoordinate,
    Coordinate,
    CoordinateGroup,
    PowerFeedCoordinate,
    PowerPanelCoordinate,
    VirtualMachineCoordinate,
)


class CoordinateGroupListTable(BaseTable):
    name = tables.Column(
        linkify=True
    )
    devices = tables.Column()

    class Meta(BaseTable.Meta):
        model = CoordinateGroup
        fields = ('pk', 'id', 'name', 'description', 'devices')
        default_columns = ('name', 'description', 'devices')

class CircuitCoordinateListTable(BaseTable):
    group = tables.Column(
        linkify=True
    )

    device = tables.Column(
        linkify=True
    )

    class Meta(BaseTable.Meta):
        model = CircuitCoordinate
        fields = ('pk', 'id', 'group', 'device', 'x', 'y')
        default_columns = ('id', 'group', 'device', 'x', 'y')

class PowerPanelCoordinateListTable(BaseTable):
    group = tables.Column(
        linkify=True
    )

    device = tables.Column(
        linkify=True
    )

    class Meta(BaseTable.Meta):
        model = PowerPanelCoordinate
        fields = ('pk', 'id', 'group', 'device', 'x', 'y')
        default_columns = ('id', 'group', 'device', 'x', 'y')

class PowerFeedCoordinateListTable(BaseTable):
    group = tables.Column(
        linkify=True
    )

    device = tables.Column(
        linkify=True
    )

    class Meta(BaseTable.Meta):
        model = PowerFeedCoordinate
        fields = ('pk', 'id', 'group', 'device', 'x', 'y')
        default_columns = ('id', 'group', 'device', 'x', 'y')

class VirtualMachineCoordinateListTable(BaseTable):
    group = tables.Column(
        linkify=True
    )

    device = tables.Column(
        linkify=True,
        verbose_name='Virtual machine',
    )

    class Meta(BaseTable.Meta):
        model = VirtualMachineCoordinate
        fields = ('pk', 'id', 'group', 'device', 'x', 'y')
        default_columns = ('id', 'group', 'device', 'x', 'y')

class CoordinateListTable(BaseTable):
    group = tables.Column(
        linkify=True
    )

    device = tables.Column(
        linkify=True
    )

    class Meta(BaseTable.Meta):
        model = Coordinate
        fields = ('pk', 'id', 'group', 'device', 'x', 'y')
        default_columns = ('id', 'group', 'device', 'x', 'y')
