import json
import uuid
from functools import reduce
from itertools import chain
from typing import DefaultDict, Dict, Optional, Union

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import Lower
from django.http import HttpRequest, HttpResponseRedirect, QueryDict
from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from django_tables2 import RequestConfig
from nautobot.apps.views import (
    BulkImportView,
    ObjectDeleteView,
    ObjectEditView,
    ObjectListView,
    ObjectView,
)
from nautobot.circuits.models import Circuit, CircuitTermination, ProviderNetwork
from nautobot.dcim.models import (
    Cable,
    Device,
    DeviceType,
    FrontPort,
    Interface,
    PowerFeed,
    PowerPanel,
    RearPort,
)
from nautobot.extras.models import Role, Tag
from nautobot.extras.views import ObjectChangeLogView

# Nautobot 3.2 replaced the Cable termination GFK fields and the PathEndpoint
# `_path` FK with a CableToCableTermination join table and a `cable_paths`
# GenericRelation (dcim migrations 0088-0096). Feature-detect so this app
# keeps working on both older and newer Nautobot releases.
HAS_CABLE_PATHS = hasattr(Interface, "cable_paths")

import nautobot_topology_views.models
from nautobot_topology_views.choices import NodeLabelItems
from nautobot_topology_views.filters import (
    CircuitCoordinateFilterSet,
    CoordinateFilterSet,
    CoordinateGroupFilterSet,
    DeviceFilterSet,
    PowerFeedCoordinateFilterSet,
    PowerPanelCoordinateFilterSet,
)
from nautobot_topology_views.forms import (
    CircuitCoordinatesFilterForm,
    CircuitCoordinatesForm,
    CircuitCoordinatesImportForm,
    CoordinateGroupsForm,
    CoordinateGroupsImportForm,
    CoordinatesFilterForm,
    CoordinatesForm,
    CoordinatesImportForm,
    DeviceFilterForm,
    IndividualOptionsForm,
    PowerFeedCoordinatesFilterForm,
    PowerFeedCoordinatesForm,
    PowerFeedCoordinatesImportForm,
    PowerPanelCoordinatesFilterForm,
    PowerPanelCoordinatesForm,
    PowerPanelCoordinatesImportForm,
)
from nautobot_topology_views.models import (
    CircuitCoordinate,
    Coordinate,
    CoordinateGroup,
    IndividualOptions,
    PowerFeedCoordinate,
    PowerPanelCoordinate,
    RoleImage,
)
from nautobot_topology_views.tables import (
    CircuitCoordinateListTable,
    CoordinateGroupListTable,
    CoordinateListTable,
    PowerFeedCoordinateListTable,
    PowerPanelCoordinateListTable,
)
from nautobot_topology_views.utils import (
    CONF_IMAGE_DIR,
    IMAGE_FILETYPES,
    LinePattern,
    abbreviate_interface_name,
    find_image_url,
    get_model_role,
    get_model_slug,
    get_query_settings,
    image_static_url,
)


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


def get_image_for_entity(entity: Union[Device, Circuit, PowerPanel, PowerFeed]):
    is_device = isinstance(entity, Device)
    query = (
        {"content_type_id": ContentType.objects.get_for_model(Role).pk, "object_id": entity.role_id}
        if is_device
        else {"content_type_id": ContentType.objects.get_for_model(entity).pk, "object_id": None}
    )

    try:
        return RoleImage.objects.get(**query).get_image_url()
    except RoleImage.DoesNotExist:
        return find_image_url(
            entity.role.name if is_device else get_model_slug(entity.__class__)
        )


def create_node(
    device: Union[Device, Circuit, PowerPanel, PowerFeed],
    save_coords: bool,
    node_label_items: list,
    group_id="default"
):
    node = {}
    node_content = ""
    if isinstance(device, Circuit):
        dev_name = device.cid
        node["id"] = f"c{device.pk}"
        model_name = 'CircuitCoordinate'

        if device.provider is not None:
            node_content += (
                f"<tr><th>Provider: </th><td>{device.provider.name}</td></tr>"
            )
        circuit_type = getattr(device, "circuit_type", None) or getattr(device, "type", None)
        if circuit_type is not None:
            node_content += f"<tr><th>Type: </th><td>{circuit_type.name}</td></tr>"
    elif isinstance(device, PowerPanel):
        dev_name = device.name
        node["id"] = f"p{device.pk}"
        model_name = 'PowerPanelCoordinate'

        if device.location is not None:
            node_content += (
                f"<tr><th>Location: </th><td>{device.location.name}</td></tr>"
            )
    elif isinstance(device, PowerFeed):
        dev_name = device.name
        node["id"] = f"f{device.pk}"
        model_name = 'PowerFeedCoordinate'

        if device.power_panel is not None:
            node_content += (
                f"<tr><th>Power Panel: </th><td>{device.power_panel.name}</td></tr>"
            )
        if device.type is not None:
            node_content += f"<tr><th>Type: </th><td>{device.type}</td></tr>"
        if device.supply is not None:
            node_content += f"<tr><th>Supply: </th><td>{device.supply}</td></tr>"
        if device.phase is not None:
            node_content += f"<tr><th>Phase: </th><td>{device.phase}</td></tr>"
        if device.amperage is not None:
            node_content += f"<tr><th>Amperage: </th><td>{device.amperage}</td></tr>"
        if device.voltage is not None:
            node_content += f"<tr><th>Voltage: </th><td>{device.voltage}</td></tr>"
    else:
        model_name = 'Coordinate'
        dev_name = device.name
        if dev_name is None:
            dev_name = device.device_type.full_name

        if device.device_type is not None:
            node_content += (
                f"<tr><th>Type: </th><td>{device.device_type.model}</td></tr>"
            )
        if device.role.name is not None:
            node_content += (
                f"<tr><th>Role: </th><td>{device.role.name}</td></tr>"
            )
        if device.serial != "":
            node_content += f"<tr><th>Serial: </th><td>{device.serial}</td></tr>"
        if device.primary_ip is not None:
            node_content += (
                f"<tr><th>IP Address: </th><td>{device.primary_ip.address}</td></tr>"
            )
        if device.location is not None:
            node_content += (
                f"<tr><th>Location: </th><td>{device.location.name}</td></tr>"
            )
        if device.rack is not None:
            node_content += f"<tr><th>Rack: </th><td>{device.rack.name}</td></tr>"
        if device.position is not None:
            if device.face is not None:
                node_content += f"<tr><th>Position: </th><td>{device.position} ({device.face})</td></tr>"
            else:
                node_content += (
                    f"<tr><th>Position: </th><td>{device.position}</td></tr>"
                )

        node["id"] = device.pk

        if device.location is not None:
            node["location"] = device.location.name
            node["location_id"] = device.location_id
        if device.rack is not None:
            node["rack"] = device.rack.name
            node["rack_id"] = device.rack_id
        if device.virtual_chassis is not None:
            node["virtual_chassis"] = device.virtual_chassis.name
            node["virtual_chassis_id"] = device.virtual_chassis_id

        if device.role.color != "":
            node["color.border"] = "#" + device.role.color

    model_class = getattr(nautobot_topology_views.models, model_name)

    if group_id is None or group_id == "default":
        group_id = model_class.get_or_create_default_group(group_id)
        if not group_id:
            print('Exception occured while handling default group.')
            return node

    group = get_object_or_404(CoordinateGroup, pk=group_id)

    node["physics"] = True
    # Coords must be set even if no coords have been stored. Otherwise nodes with coords
    # will not be placed correctly by vis-network.
    node["x"] = 0
    node["y"] = 0
    if model_class.objects.filter(group=group, device=device.pk).values('x') and model_class.objects.filter(group=group, device=device.pk).values('y'):
        # Coordinates data for the device exists in Coordinates Group. Let's assign them
        node["x"] = model_class.objects.get(group=group, device=device.pk).x
        node["y"] = model_class.objects.get(group=group, device=device.pk).y
        node["physics"] = False
    elif "coordinates" in device.custom_field_data:
        # We prefer the new Coordinate model but leave the deprecated method
        # for now as fallback for compatibility reasons
        if device.custom_field_data["coordinates"] is not None:
            if ";" in device.custom_field_data["coordinates"]:
                cords = device.custom_field_data["coordinates"].split(";")
                node["x"] = int(cords[0])
                node["y"] = int(cords[1])
                node["physics"] = False

    dev_title = "<table><tbody> %s</tbody></table>" % (node_content)
    node["title"] = dev_title
    node["name"] = dev_name

    # Create a list of possible label items. Omit None types
    label_mapping = {
        NodeLabelItems.DEVICE_NAME: dev_name,
        NodeLabelItems.DEVICE_TYPE: getattr(device, 'device_type', None),
        NodeLabelItems.ROLE: getattr(device, 'role', None),
        NodeLabelItems.DESCRIPTION: getattr(device, 'description', None),
        NodeLabelItems.PRIMARY_IPV4: getattr(device, 'primary_ip4', None),
        NodeLabelItems.PRIMARY_IPV6: getattr(device, 'primary_ip6', None),
        NodeLabelItems.OUT_OF_BAND_IP: getattr(device, 'oob_ip', None),
        NodeLabelItems.PLATFORM: getattr(device, 'platform', None),
        NodeLabelItems.SERIAL: getattr(device, 'serial', None),
        NodeLabelItems.TENANT: getattr(device, 'tenant', None),
        NodeLabelItems.SITE: getattr(device, 'location', None),
        NodeLabelItems.LOCATION: getattr(device, 'location', None),
        NodeLabelItems.RACK: getattr(device, 'rack', None),
        NodeLabelItems.VIRTUAL_CHASSIS: getattr(device, 'virtual_chassis', None),
        NodeLabelItems.ASSET_TAG: getattr(device, 'asset_tag', None),
    }

    label_items = []
    for item in node_label_items:
        if label_mapping[item] and label_mapping[item] is not None:
            label_items.append(str(label_mapping[item]))
    node_label = '\n'.join(label_items)

    node["label"] = node_label
    node["shape"] = "image"
    node["href"] = device.get_absolute_url()
    node["image"] = get_image_for_entity(device)
    node["label_num_lines"] = len(label_items)

    return node


def create_edge(
    edge_id: int,
    termination_a: Dict,
    termination_b: Dict,
    straight_cables: bool,
    draw_termination_labels: bool,
    draw_cable_labels: bool,
    circuit: Optional[Dict] = None,
    cable: Optional[Cable] = None,
    wireless: Optional[Dict] = None,
    power: Optional[bool] = None,
    interface: Optional[Interface] = None,
):
    cable_a_name = (
        "device A name unknown"
        if termination_a["termination_name"] is None
        else termination_a["termination_name"]
    )
    cable_a_dev_name = (
        "device A name unknown"
        if termination_a["termination_device_name"] is None
        else termination_a["termination_device_name"]
    )
    cable_b_name = (
        "device A name unknown"
        if termination_b["termination_name"] is None
        else termination_b["termination_name"]
    )
    cable_b_dev_name = (
        "cable B name unknown"
        if termination_b["termination_device_name"] is None
        else termination_b["termination_device_name"]
    )

    edge = {}
    edge["id"] = edge_id
    edge["from"] = termination_a["device_id"]
    edge["to"] = termination_b["device_id"]
    edge["color"] = '#2b7ce9'
    title = "Cable"

    if circuit is not None:
        edge["dashes"] = True
        title = f"Circuit provider: {circuit['provider_name']}<br>Termination"

    elif wireless is not None:
        edge["dashes"] = LinePattern().wireless
        title = "Wireless Connection"

    elif power is not None:
        edge["dashes"] = LinePattern().power
        title = "Power Connection"

    elif interface is not None:
        title = "Interface Connection"
        edge["width"] = 3
        edge["dashes"] = LinePattern().logical
        edge["color"] = '#f1c232'
        edge["href"] = interface.get_absolute_url() + "trace"

    if cable is not None and hasattr(cable, "label") and cable.label:
        cable_label = "<br>Label: " + cable.label
        if draw_cable_labels is True:
            edge["label"] = cable.label
    else:
        cable_label = ""

    edge[
        "title"
    ] = f"{title} between<br>{cable_a_dev_name} [{cable_a_name}]<br>{cable_b_dev_name} [{cable_b_name}] {cable_label}"

    if cable is not None:
        edge["href"] = cable.get_absolute_url()
        if hasattr(cable, 'color') and cable.color != "":
            edge["color"] = "#" + cable.color

    # if straight_cables == True: edge["smooth"] = False
    edge["smooth"] = not straight_cables

    if draw_termination_labels is True:
        edge["drawTerminationLabel"] = True
        edge["cable_a_name"] = abbreviate_interface_name(cable_a_name)
        edge["cable_b_name"] = abbreviate_interface_name(cable_b_name)


    return edge


def cable_side_endpoints(cable, side):
    """Endpoint objects on one cable side ('a'/'b') across Nautobot versions.

    Nautobot 3.2's terminations_a/terminations_b return CableToCableTermination
    join rows (each carrying .termination); the older NetBox-style
    a_terminations/b_terminations were the endpoint objects directly.
    """
    rows = getattr(cable, f"terminations_{side}", None)
    if rows is not None:
        return [r.termination for r in rows if getattr(r, "termination", None) is not None]
    return list(getattr(cable, f"{side}_terminations", []) or [])


def create_circuit_termination(termination):
    if isinstance(termination, CircuitTermination):
        return {
            "termination_name": termination.circuit.provider.name,
            "termination_device_name": termination.circuit.cid,
            "device_id": "c{}".format(termination.circuit.pk),
        }
    if (
        isinstance(termination, Interface)
        or isinstance(termination, FrontPort)
        or isinstance(termination, RearPort)
    ):
        return {
            "termination_name": termination.name,
            "termination_device_name": termination.device.name,
            "device_id": termination.device.pk,
        }
    return None


def get_topology_data(
    queryset: QuerySet,
    individualOptions: IndividualOptions,
    show_unconnected: bool,
    ignore_cable_type: list,
    save_coords: bool,
    show_cables: bool,
    show_circuit: bool,
    show_logical_connections: bool,
    show_single_cable_logical_conns: bool,
    show_neighbors: bool,
    show_power: bool,
    show_wireless: bool,
    group_sites: bool,
    group_locations: bool,
    group_racks: bool,
    group_virtualchassis: bool,
    group_id,
    straight_cables: bool,
    draw_termination_labels: bool,
    draw_cable_labels: bool,
    grid_size: list,
    node_label_items: list,
):

    supported_termination_types = []
    for t in IndividualOptions.CHOICES:
        supported_termination_types.append(t[1])

    if not queryset:
        return None

    nodes_devices = {}
    edges = []
    nodes = []
    options = {}
    edge_ids = 0
    nodes_circuits: Dict[int, Circuit] = {}
    nodes_powerpanel: Dict[int, PowerPanel] = {}
    nodes_powerfeed: Dict[int, PowerFeed] = {}
    nodes_provider_networks = {}
    cable_ids = DefaultDict(dict)
    interface_ids = DefaultDict(dict)

    device_ids = [d.pk for d in queryset]
    location_ids = [d.location_id for d in queryset if d.location_id]

    if show_neighbors:
        interfaces = Interface.objects.filter(
            Q(device_id__in=device_ids)
        )
        frontports = FrontPort.objects.filter(
            Q(device_id__in=device_ids)
        )
        rearports = RearPort.objects.filter(
            Q(device_id__in=device_ids)
        )

        ports = chain(interfaces, frontports, rearports)
        for port in ports:
            for link_peer in port.link_peers:
                if hasattr(link_peer, 'device') and link_peer.device.id not in device_ids:
                    device_ids.append(link_peer.device.id)

        if show_logical_connections:
            path_complete_interfaces = Interface.objects.filter(
                (Q(cable_paths__destination_id__isnull=False) if HAS_CABLE_PATHS else Q(_path__destination_id__isnull=False)) & Q(device_id__in=device_ids)
            )
            for path_complete_interface in path_complete_interfaces:
                connected_endpoint = path_complete_interface.connected_endpoint
                if connected_endpoint is not None and not isinstance(connected_endpoint, ProviderNetwork):
                    device_ids.append(connected_endpoint.device.id)

    if show_circuit:
        circuit_terminations = CircuitTermination.objects.filter(
            Q(location_id__in=location_ids) | Q(provider_network__isnull=False)
        )
        for circuit_termination in circuit_terminations:
            circuit_termination: CircuitTermination
            if (
                show_unconnected
                and circuit_termination.circuit_id not in nodes_circuits
            ):
                nodes_circuits[
                    circuit_termination.circuit.pk
                ] = circuit_termination.circuit

            termination_a = {}
            termination_b = {}
            circuit_model = {}
            cable_endpoints_a = cable_endpoints_b = []
            if circuit_termination.cable is not None:
                cable_endpoints_a = cable_side_endpoints(circuit_termination.cable, "a")
                cable_endpoints_b = cable_side_endpoints(circuit_termination.cable, "b")
            if bool(cable_endpoints_a) and bool(cable_endpoints_b):
                termination_a = create_circuit_termination(cable_endpoints_a[0])
                termination_b = create_circuit_termination(cable_endpoints_b[0])
            elif getattr(circuit_termination, "provider_network", None) is not None:
                # Nautobot has no generic CircuitTermination.termination attribute
                # (a NetBox-ism); the non-cable case that matters here is a
                # termination pointing at a provider network.
                if (
                    circuit_termination.provider_network_id
                    not in nodes_provider_networks
                ):
                    nodes_provider_networks[
                        circuit_termination.provider_network.pk
                    ] = circuit_termination.provider_network

            if bool(termination_a) and bool(termination_b):
                circuit_model = {
                    "provider_name": circuit_termination.circuit.provider.name
                }
                edge_ids += 1
                edges.append(
                    create_edge(
                        edge_id=edge_ids,
                        cable=circuit_termination.cable,
                        circuit=circuit_model,
                        termination_a=termination_a,
                        termination_b=termination_b,
                        straight_cables=straight_cables,
                        draw_termination_labels=draw_termination_labels,
                        draw_cable_labels=draw_cable_labels,
                    )
                )

                circuit_has_connections = False
                for termination in [
                    cable_endpoints_a[0],
                    cable_endpoints_b[0],
                ]:
                    if not isinstance(termination, CircuitTermination):
                        if (
                            termination.device_id not in nodes_devices
                            and termination.device_id in device_ids
                        ):
                            nodes_devices[termination.device_id] = termination.device
                            circuit_has_connections = True
                        else:
                            if termination.device_id in device_ids:
                                circuit_has_connections = True

                if circuit_has_connections and not show_unconnected:
                    if circuit_termination.circuit_id not in nodes_circuits:
                        nodes_circuits[
                            circuit_termination.circuit.pk
                        ] = circuit_termination.circuit

        for d in nodes_circuits.values():
            nodes.append(create_node(d, save_coords, node_label_items, group_id))

    if show_power:
        power_panels_ids = PowerPanel.objects.filter(
            Q(location_id__in=location_ids)
        ).values_list("pk", flat=True)
        power_feeds: QuerySet[PowerFeed] = PowerFeed.objects.filter(
            Q(power_panel_id__in=power_panels_ids)
        )

        for power_feed in power_feeds:
            if show_unconnected or (
                not show_unconnected and power_feed.cable_id is not None
            ):
                if power_feed.power_panel_id not in nodes_powerpanel:
                    nodes_powerpanel[power_feed.power_panel.pk] = power_feed.power_panel

                power_link_name = ""
                if power_feed.pk not in nodes_powerfeed:
                    if not show_unconnected:
                        if power_feed.link_peers[0].device_id in device_ids:
                            nodes_powerfeed[power_feed.pk] = power_feed
                            power_link_name = power_feed.link_peers[0].name
                    else:
                        nodes_powerfeed[power_feed.pk] = power_feed

                edge_ids += 1
                termination_a = {
                    "termination_name": power_feed.power_panel.name,
                    "termination_device_name": "",
                    "device_id": f"p{power_feed.power_panel_id}",
                }
                termination_b = {
                    "termination_name": power_feed.name,
                    "termination_device_name": power_link_name,
                    "device_id": f"f{power_feed.pk}",
                }
                edges.append(
                    create_edge(
                        edge_id=edge_ids,
                        termination_a=termination_a,
                        termination_b=termination_b,
                        power=True,
                        straight_cables=straight_cables,
                        draw_termination_labels=draw_termination_labels,
                        draw_cable_labels=draw_cable_labels,
                    )
                )

                if power_feed.cable_id is not None:
                    cable_ids[power_feed.cable_id][power_feed.cable_end] = termination_b

        for d in nodes_powerfeed.values():
            nodes.append(create_node(d, save_coords, node_label_items ,group_id))

        for d in nodes_powerpanel.values():
            nodes.append(create_node(d, save_coords, node_label_items, group_id))

    if show_logical_connections:
        interfaces = Interface.objects.filter(
            (Q(cable_paths__destination_id__isnull=False) if HAS_CABLE_PATHS else Q(_path__destination_id__isnull=False)) & Q(device_id__in=device_ids)
        )

        for interface in interfaces:
            path_obj = interface.path if HAS_CABLE_PATHS else interface._path
            destination = path_obj.destination if path_obj else None
            if destination is not None:
                if isinstance(destination, Interface):
                    if destination.device.id not in device_ids:
                        # print('Destination interface not in device queryset, ignoring')
                        continue

                    if destination.id in interface_ids:
                        # we've already captured the destination interface, ignore this connection
                        # print('Destination interface already exists, ignoring')
                        continue

                    if not show_single_cable_logical_conns and interface.cable_id==destination.cable_id and show_cables:
                        # interface connection is the same as the cable connection, ignore this connection
                        continue

                    interface_ids[interface.id]=interface
                    edge_ids += 1
                    termination_a = { "termination_name": interface.name, "termination_device_name": interface.device.name, "device_id": interface.device.id }
                    termination_b = { "termination_name": destination.name, "termination_device_name": destination.device.name, "device_id": destination.device.id }
                    edges.append(create_edge(edge_id=edge_ids, termination_a=termination_a, termination_b=termination_b, interface=interface, straight_cables=straight_cables, draw_termination_labels=draw_termination_labels, draw_cable_labels=draw_cable_labels))
                    nodes_devices[interface.device.id] = interface.device
                    nodes_devices[destination.device.id] = destination.device

    if show_cables:
        if HAS_CABLE_PATHS:
            # Nautobot >= 3.2: the GFK device-id fields are gone; filter through the
            # typed termination M2Ms and prefetch the join rows so the backward-compat
            # termination_a/termination_b properties resolve without extra queries.
            cables: QuerySet[Cable] = Cable.objects.filter(
                Q(interfaces__device_id__in=device_ids)
                | Q(console_ports__device_id__in=device_ids)
                | Q(console_server_ports__device_id__in=device_ids)
                | Q(power_ports__device_id__in=device_ids)
                | Q(power_outlets__device_id__in=device_ids)
                | Q(front_ports__device_id__in=device_ids)
                | Q(rear_ports__device_id__in=device_ids)
            ).distinct().prefetch_related("terminations")
        else:
            cables: QuerySet[Cable] = Cable.objects.filter(
                Q(_termination_a_device_id__in=device_ids) | Q(_termination_b_device_id__in=device_ids)
            ).select_related("termination_a_type", "termination_b_type")

        for cable in cables:
            type_a = cable.termination_a_type.model if cable.termination_a_type else None
            type_b = cable.termination_b_type.model if cable.termination_b_type else None

            if type_a in ignore_cable_type or type_b in ignore_cable_type:
                continue

            if type_a not in supported_termination_types or type_b not in supported_termination_types:
                continue

            term_a = cable.termination_a
            term_b = cable.termination_b

            if term_a is None or term_b is None:
                continue

            if not hasattr(term_a, "device") or not hasattr(term_b, "device"):
                continue

            if term_a.device_id not in nodes_devices:
                nodes_devices[term_a.device_id] = term_a.device

            if term_b.device_id not in nodes_devices:
                nodes_devices[term_b.device_id] = term_b.device

            termination_a = {
                "termination_name": term_a.name,
                "termination_device_name": term_a.device.name,
                "device_id": term_a.device_id,
            }
            termination_b = {
                "termination_name": term_b.name,
                "termination_device_name": term_b.device.name,
                "device_id": term_b.device_id,
            }

            edge_ids += 1
            edges.append(
                create_edge(
                    edge_id=edge_ids,
                    cable=cable,
                    termination_a=termination_a,
                    termination_b=termination_b,
                    straight_cables=straight_cables,
                    draw_termination_labels=draw_termination_labels,
                    draw_cable_labels=draw_cable_labels,
                )
            )

    # if show_wireless:
    #     wlan_links: QuerySet[WirelessLink] = WirelessLink.objects.filter(
    #         Q(_interface_a_device_id__in=device_ids)
    #         & Q(_interface_b_device_id__in=device_ids)
    #     )

    #     for wlan_link in wlan_links:
    #         if wlan_link.interface_a.device_id not in nodes_devices:
    #             nodes_devices[
    #                 wlan_link.interface_a.device.pk
    #             ] = wlan_link.interface_a.device
    #         if wlan_link.interface_b.device_id not in nodes_devices:
    #             nodes_devices[
    #                 wlan_link.interface_b.device.pk
    #             ] = wlan_link.interface_b.device

    #         termination_a = {
    #             "termination_name": wlan_link.interface_a.name,
    #             "termination_device_name": wlan_link.interface_a.device.name,
    #             "device_id": wlan_link.interface_a.device_id,
    #         }
    #         termination_b = {
    #             "termination_name": wlan_link.interface_b.name,
    #             "termination_device_name": wlan_link.interface_b.device.name,
    #             "device_id": wlan_link.interface_b.device_id,
    #         }
    #         wireless = {"ssid": wlan_link.ssid}

    #         edge_ids += 1
    #         edges.append(
    #             create_edge(
    #                 edge_id=edge_ids,
    #                 cable=wlan_link,
    #                 termination_a=termination_a,
    #                 termination_b=termination_b,
    #                 wireless=wireless,
    #                 straight_cables=straight_cables,
    #                 draw_termination_labels=draw_termination_labels,
    #                 draw_cable_labels=draw_cable_labels,
    #             )
    #         )

    if group_locations:
        options['group_locations'] = 'on'
    if group_racks:
        options['group_racks'] = 'on'
    if group_sites:
        options['group_sites'] = 'on'
    if group_virtualchassis:
        options['group_virtualchassis'] = 'on'
    if grid_size:
        options['grid_size'] = grid_size
    else:
        options['grid_size'] = list('0')

    for qs_device in queryset:
        if qs_device.pk not in nodes_devices and show_unconnected:
            nodes_devices[qs_device.pk] = qs_device

    results = {}

    for d in nodes_devices.values():
        nodes.append(create_node(d, save_coords, node_label_items, group_id))

    results["nodes"] = nodes
    results["edges"] = edges
    results["group"] = group_id
    results["options"] = options
    return results


class TopologyHomeView(PermissionRequiredMixin, View):
    permission_required = ("dcim.view_location", "dcim.view_device")

    """
    Show the home page
    """

    def get(self, request):
        self.filterset = DeviceFilterSet
        self.queryset = Device.objects.restrict(request.user, 'view').select_related(
            "device_type", "role"
        )
        self.queryset = self.filterset(request.GET, self.queryset).qs
        self.model = self.queryset.model
        topo_data = None

        individualOptions, created = IndividualOptions.objects.get_or_create(
            user=request.user,
        )

        if request.GET:

            filter_id, ignore_cable_type, save_coords, show_unconnected, show_power, show_circuit, show_logical_connections, show_single_cable_logical_conns, show_cables, show_wireless, group_sites, group_locations, group_racks, group_virtualchassis, group, show_neighbors, straight_cables, draw_termination_labels, draw_cable_labels, grid_size, node_label_items = get_query_settings(request)

            filter_required = True
            empty_result = False

            if not request.GET.get("group"):
                group_id = "default"
            else:
                group_id = request.GET["group"]

            if not "draw_init" in request.GET or "draw_init" in request.GET and request.GET["draw_init"].lower() == "true":
                filter_required = False

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

                if topo_data is None or not topo_data["nodes"]:
                    empty_result = True

        else:
            # No GET-Request in URL. We most likely came here from the navigation menu.
            preselected_device_roles = IndividualOptions.objects.get(id=individualOptions.id).preselected_device_roles.all().values_list('id', flat=True)
            preselected_tags = IndividualOptions.objects.get(id=individualOptions.id).preselected_tags.all().values_list('name', flat=True)
            ignore_cable_type = IndividualOptions.objects.get(id=individualOptions.id).ignore_cable_type.translate({ord(i): None for i in '[]\''}).split(', ')
            if ignore_cable_type == ['']: ignore_cable_type = []

            q = QueryDict(mutable=True)
            q.setlist("role_id", list(preselected_device_roles))
            q.setlist("tag", list(preselected_tags))
            q.setlist("ignore_cable_type", ignore_cable_type)

            if individualOptions.save_coords: q['save_coords'] = "True"
            if individualOptions.show_unconnected: q['show_unconnected'] = "True"
            if individualOptions.show_cables: q['show_cables'] = "True"
            if individualOptions.show_logical_connections: q['show_logical_connections'] = "True"
            if individualOptions.show_single_cable_logical_conns: q['show_single_cable_logical_conns'] = "True"
            if individualOptions.show_neighbors: q['show_neighbors'] = "True"
            if individualOptions.show_circuit: q['show_circuit'] = "True"
            if individualOptions.show_power: q['show_power'] = "True"
            if individualOptions.show_wireless: q['show_wireless'] = "True"
            if individualOptions.group_sites: q['group_sites'] = "True"
            if individualOptions.group_locations: q['group_locations'] = "True"
            if individualOptions.group_racks: q['group_racks'] = "True"
            if individualOptions.group_virtualchassis: q['group_virtualchassis'] = "True"
            if individualOptions.straight_cables: q['straight_cables'] = "True"
            if individualOptions.draw_termination_labels: q['draw_termination_labels'] = "True"
            if individualOptions.draw_cable_labels: q['draw_cable_labels'] = "True"
            if individualOptions.grid_size: q['grid_size'] = individualOptions.grid_size
            node_label_items = IndividualOptions.objects.get(id=individualOptions.id).node_label_items.translate({ord(i): None for i in '[]\''}).split(', ')
            if node_label_items == ['']: node_label_items = []
            q.setlist("node_label_items", node_label_items)

            if individualOptions.draw_default_layout:
                q['draw_init'] = "True"
            else:
                q['draw_init'] = "False"

            query_string = q.urlencode()
            return HttpResponseRedirect(f"{request.path}?{query_string}")

        return render(
            request,
            "nautobot_topology_views/index.html",
            {
                "filter_form": DeviceFilterForm(request.GET, label_suffix=""),
                "topology_data": json.dumps(topo_data, cls=UUIDEncoder),
                "broken_image": find_image_url("role-unknown"),
                "model": self.model,
                "basepath": getattr(settings, "BASE_PATH", ""),
                "filter_required": filter_required,
                "empty_result": empty_result,
            },
        )


CONFIG = settings.PLUGINS_CONFIG["nautobot_topology_views"]
ADDITIONAL_ROLES = (PowerPanel, PowerFeed, Circuit)


class LocationTopologyView(PermissionRequiredMixin, View):
    """Render the topology view filtered to a specific location, for use as a tab on the Location detail page."""

    permission_required = ("dcim.view_location", "dcim.view_device")

    def get(self, request, pk):
        from nautobot.dcim.models import Location

        location = get_object_or_404(Location.objects.restrict(request.user, "view"), pk=pk)

        individualOptions, _ = IndividualOptions.objects.get_or_create(user=request.user)

        # Build filter query dict with location pre-applied
        q = QueryDict(mutable=True)
        q.setlist("location_id", [str(pk)])

        queryset = Device.objects.restrict(request.user, "view").select_related("device_type", "role")
        queryset = DeviceFilterSet(q, queryset).qs

        # Resolve display options from IndividualOptions
        save_coords = individualOptions.save_coords
        if save_coords and not settings.PLUGINS_CONFIG["nautobot_topology_views"]["allow_coordinates_saving"]:
            save_coords = False
            messages.warning(request, "Coordinate saving not allowed. Setting has been overridden")
        elif settings.PLUGINS_CONFIG["nautobot_topology_views"]["always_save_coordinates"]:
            save_coords = True

        ignore_cable_type = individualOptions.ignore_cable_type.translate({ord(i): None for i in "[]'"}).split(", ")
        if ignore_cable_type == [""]:
            ignore_cable_type = []

        node_label_items = individualOptions.node_label_items.translate({ord(i): None for i in "[]'"}).split(", ")
        if node_label_items == [""]:
            node_label_items = []

        topo_data = get_topology_data(
            queryset=queryset,
            individualOptions=individualOptions,
            ignore_cable_type=ignore_cable_type,
            save_coords=save_coords,
            show_unconnected=individualOptions.show_unconnected,
            show_cables=individualOptions.show_cables,
            show_logical_connections=individualOptions.show_logical_connections,
            show_single_cable_logical_conns=individualOptions.show_single_cable_logical_conns,
            show_neighbors=individualOptions.show_neighbors,
            show_circuit=individualOptions.show_circuit,
            show_power=individualOptions.show_power,
            show_wireless=individualOptions.show_wireless,
            group_sites=individualOptions.group_sites,
            group_locations=individualOptions.group_locations,
            group_racks=individualOptions.group_racks,
            group_virtualchassis=individualOptions.group_virtualchassis,
            group_id="default",
            straight_cables=individualOptions.straight_cables,
            draw_termination_labels=individualOptions.draw_termination_labels,
            draw_cable_labels=individualOptions.draw_cable_labels,
            grid_size=individualOptions.grid_size,
            node_label_items=node_label_items,
        )

        empty_result = topo_data is None or not topo_data.get("nodes")

        return render(
            request,
            "nautobot_topology_views/index.html",
            {
                "filter_form": DeviceFilterForm(q, label_suffix=""),
                "topology_data": json.dumps(topo_data, cls=UUIDEncoder),
                "broken_image": find_image_url("role-unknown"),
                "model": queryset.model,
                "basepath": getattr(settings, "BASE_PATH", ""),
                "filter_required": False,
                "empty_result": empty_result,
                "location": location,
            },
        )


class TopologyImagesView(PermissionRequiredMixin, View):
    permission_required = (
        "dcim.view_site",
        "dcim.view_role",
        "dcim.add_role",
        "dcim.change_role",
    )

    def get(self, request: HttpRequest):
        images = [
            {"url": image_static_url(image), "title": image.stem}
            for image in CONF_IMAGE_DIR.iterdir() if image.name.lower().endswith(IMAGE_FILETYPES)
        ]

        roles = reduce(
            lambda acc, cur: {
                **acc,
                cur.name: {
                    "id": cur.pk,
                    "name": cur.name,
                    "slug": cur.name,
                    "image": find_image_url(cur.name),
                },
            },
            Role.objects.all(),
            dict(),
        )

        for additional_role in ADDITIONAL_ROLES:
            cur = get_model_role(additional_role)
            ct = ContentType.objects.get_for_model(additional_role).pk

            roles[cur.name] = {
                "id": f"ct{ct}",
                "name": cur.name,
                "slug": cur.slug,
                "image": find_image_url(cur.slug),
            }

        role_images = RoleImage.objects.all()

        for role_image in role_images:
            roles[role_image.role_data.name]["image"] = role_image.get_image_url()

        return render(
            request,
            "nautobot_topology_views/images.html",
            {
                "roles": sorted(list(roles.values()), key=lambda r: r["name"]),
                "images": images,
                "basepath": getattr(settings, "BASE_PATH", ""),
            },
        )

class CircuitCoordinateView(PermissionRequiredMixin, ObjectView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = CircuitCoordinate.objects.all()

class CircuitCoordinateAddView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.add_coordinate'

    queryset = CircuitCoordinate.objects.all()
    model_form = CircuitCoordinatesForm
    template_name = 'nautobot_topology_views/circuitcoordinate_add.html'

class CircuitCoordinateBulkImportView(BulkImportView):
    queryset = CircuitCoordinate.objects.all()
    model_form = CircuitCoordinatesImportForm

class CircuitCoordinateListView(PermissionRequiredMixin, ObjectListView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = CircuitCoordinate.objects.all()
    table = CircuitCoordinateListTable
    template_name = 'nautobot_topology_views/circuitcoordinate_list.html'
    filterset_class = CircuitCoordinateFilterSet
    filterset_form = CircuitCoordinatesFilterForm

class CircuitCoordinateEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.change_coordinate'

    queryset = CircuitCoordinate.objects.all()
    model_form = CircuitCoordinatesForm
    template_name = 'nautobot_topology_views/circuitcoordinate_edit.html'

class CircuitCoordinateDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'nautobot_topology_views.delete_coordinate'

    queryset = CircuitCoordinate.objects.all()

class CircuitCoordinateChangeLogView(PermissionRequiredMixin, ObjectChangeLogView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = CircuitCoordinate.objects.all()

class PowerPanelCoordinateView(PermissionRequiredMixin, ObjectView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = PowerPanelCoordinate.objects.all()

class PowerPanelCoordinateAddView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.add_coordinate'

    queryset = PowerPanelCoordinate.objects.all()
    model_form = PowerPanelCoordinatesForm
    template_name = 'nautobot_topology_views/powerpanelcoordinate_add.html'

class PowerPanelCoordinateBulkImportView(BulkImportView):
    queryset = PowerPanelCoordinate.objects.all()
    model_form = PowerPanelCoordinatesImportForm

class PowerPanelCoordinateListView(PermissionRequiredMixin, ObjectListView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = PowerPanelCoordinate.objects.all()
    table = PowerPanelCoordinateListTable
    template_name = 'nautobot_topology_views/powerpanelcoordinate_list.html'
    filterset_class = PowerPanelCoordinateFilterSet
    filterset_form = PowerPanelCoordinatesFilterForm

class PowerPanelCoordinateEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.change_coordinate'

    queryset = PowerPanelCoordinate.objects.all()
    model_form = PowerPanelCoordinatesForm
    template_name = 'nautobot_topology_views/powerpanelcoordinate_edit.html'

class PowerPanelCoordinateDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'nautobot_topology_views.delete_coordinate'

    queryset = PowerPanelCoordinate.objects.all()

class PowerPanelCoordinateChangeLogView(PermissionRequiredMixin, ObjectChangeLogView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = PowerPanelCoordinate.objects.all()

class PowerFeedCoordinateView(PermissionRequiredMixin, ObjectView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = PowerFeedCoordinate.objects.all()

class PowerFeedCoordinateAddView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.add_coordinate'

    queryset = PowerFeedCoordinate.objects.all()
    model_form = PowerFeedCoordinatesForm
    template_name = 'nautobot_topology_views/powerfeedcoordinate_add.html'

class PowerFeedCoordinateBulkImportView(BulkImportView):
    queryset = PowerFeedCoordinate.objects.all()
    model_form = PowerFeedCoordinatesImportForm

class PowerFeedCoordinateListView(PermissionRequiredMixin, ObjectListView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = PowerFeedCoordinate.objects.all()
    table = PowerFeedCoordinateListTable
    template_name = 'nautobot_topology_views/powerfeedcoordinate_list.html'
    filterset_class = PowerFeedCoordinateFilterSet
    filterset_form = PowerFeedCoordinatesFilterForm

class PowerFeedCoordinateEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.change_coordinate'

    queryset = PowerFeedCoordinate.objects.all()
    model_form = PowerFeedCoordinatesForm
    template_name = 'nautobot_topology_views/powerfeedcoordinate_edit.html'

class PowerFeedCoordinateDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'nautobot_topology_views.delete_coordinate'

    queryset = PowerFeedCoordinate.objects.all()

class PowerFeedCoordinateChangeLogView(PermissionRequiredMixin, ObjectChangeLogView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = PowerFeedCoordinate.objects.all()

class CoordinateView(PermissionRequiredMixin, ObjectView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = Coordinate.objects.all()

class CoordinateAddView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.add_coordinate'

    queryset = Coordinate.objects.all()
    model_form = CoordinatesForm
    template_name = 'nautobot_topology_views/coordinate_add.html'

class CoordinateBulkImportView(BulkImportView):
    queryset = Coordinate.objects.all()
    model_form = CoordinatesImportForm

class CoordinateListView(PermissionRequiredMixin, ObjectListView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = Coordinate.objects.all()
    table = CoordinateListTable
    template_name = 'nautobot_topology_views/coordinate_list.html'
    filterset_class = CoordinateFilterSet
    filterset_form = CoordinatesFilterForm

class CoordinateEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.change_coordinate'

    queryset = Coordinate.objects.all()
    model_form = CoordinatesForm
    template_name = 'nautobot_topology_views/coordinate_edit.html'

class CoordinateDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'nautobot_topology_views.delete_coordinate'

    queryset = Coordinate.objects.all()

class CoordinateChangeLogView(PermissionRequiredMixin, ObjectChangeLogView):
    permission_required = 'nautobot_topology_views.view_coordinate'

    queryset = Coordinate.objects.all()

class CoordinateGroupView(PermissionRequiredMixin, ObjectView):
    permission_required = 'nautobot_topology_views.view_coordinategroup'

    queryset = CoordinateGroup.objects.all()

    def get_extra_context(self, request, instance):
        circuittable = CircuitCoordinateListTable(instance.circuitcoordinate_set.all())
        RequestConfig(request).configure(circuittable)
        powerpaneltable = PowerPanelCoordinateListTable(instance.powerpanelcoordinate_set.all())
        RequestConfig(request).configure(powerpaneltable)
        powerfeedtable = PowerFeedCoordinateListTable(instance.powerfeedcoordinate_set.all())
        RequestConfig(request).configure(powerfeedtable)
        table = CoordinateListTable(instance.coordinate_set.all())
        RequestConfig(request).configure(table)

        return {
            'circuitcoordinates_table': circuittable,
            'powerpanelcoordinates_table': powerpaneltable,
            'powerfeedcoordinates_table': powerfeedtable,
            'coordinates_table': table,
        }

class CoordinateGroupAddView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.add_coordinategroup'

    queryset = CoordinateGroup.objects.all()
    model_form = CoordinateGroupsForm
    template_name = 'nautobot_topology_views/coordinategroup_add.html'

class CoordinateGroupBulkImportView(BulkImportView):
    queryset = CoordinateGroup.objects.all()
    model_form = CoordinateGroupsImportForm

class CoordinateGroupListView(PermissionRequiredMixin, ObjectListView):
    permission_required = 'nautobot_topology_views.view_coordinategroup'

    queryset = CoordinateGroup.objects.annotate(
        devices = Count('coordinate')
    )
    table = CoordinateGroupListTable
    template_name = 'nautobot_topology_views/coordinategroup_list.html'
    filterset_class = CoordinateGroupFilterSet

class CoordinateGroupEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'nautobot_topology_views.change_coordinategroup'

    queryset = CoordinateGroup.objects.all()
    model_form = CoordinateGroupsForm
    template_name = 'nautobot_topology_views/coordinategroup_edit.html'

class CoordinateGroupDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'nautobot_topology_views.delete_coordinategroup'

    queryset = CoordinateGroup.objects.all()

class CoordinateGroupChangeLogView(PermissionRequiredMixin, ObjectChangeLogView):
    permission_required = 'nautobot_topology_views.view_coordinategroup'

    queryset = CoordinateGroup.objects.all()

class TopologyIndividualOptionsView(PermissionRequiredMixin, View):
    permission_required = 'nautobot_topology_views.change_individualoptions'

    def post(self, request):
        instance = IndividualOptions.objects.get(user=request.user)
        form = IndividualOptionsForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Options have been sucessfully saved")
        else:
            messages.error(request, form.errors)

        return HttpResponseRedirect("./")

    def get(self, request):
        queryset, created = IndividualOptions.objects.get_or_create(
            user=request.user,
        )

        form = IndividualOptionsForm(
            initial={
                'user': request.user,
                'ignore_cable_type': tuple(queryset.ignore_cable_type.translate({ord(i): None for i in '[]\''}).split(', ')),
                'preselected_device_roles': IndividualOptions.objects.get(id=queryset.id).preselected_device_roles.all(),
                'preselected_tags': IndividualOptions.objects.get(id=queryset.id).preselected_tags.all(),
                'save_coords': queryset.save_coords,
                'show_unconnected': queryset.show_unconnected,
                'show_cables': queryset.show_cables,
                'show_logical_connections': queryset.show_logical_connections,
                'show_single_cable_logical_conns': queryset.show_single_cable_logical_conns,
                'show_neighbors': queryset.show_neighbors,
                'show_circuit': queryset.show_circuit,
                'show_power': queryset.show_power,
                'show_wireless': queryset.show_wireless,
                'group_sites': queryset.group_sites,
                'group_locations': queryset.group_locations,
                'group_racks': queryset.group_racks,
                'group_virtualchassis': queryset.group_virtualchassis,
                'draw_default_layout': queryset.draw_default_layout,
                'straight_cables': queryset.straight_cables,
                'draw_termination_labels': queryset.draw_termination_labels,
                'draw_cable_labels': queryset.draw_cable_labels,
                'grid_size': queryset.grid_size,
                'node_label_items': tuple(queryset.node_label_items.translate({ord(i): None for i in '[]\''}).split(', ')),
            },
        )

        return render(
            request,
            "nautobot_topology_views/individual_options.html",
            {
                "form": form,
                "object": queryset,
            },
        )
