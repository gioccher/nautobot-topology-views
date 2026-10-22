import base64
import re
import sys
import xml.dom.minidom
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Type

from django.conf import settings
from django.contrib import messages
from django.db.models import Model
from django.templatetags.static import static
from django.utils.text import camel_case_to_spaces, re_camel_case

_INTERFACE_ABBREV = [
    (re.compile(r'^HundredGigabitEthernet', re.IGNORECASE), 'Hu'),
    (re.compile(r'^FortyGigabitEthernet', re.IGNORECASE), 'Fo'),
    (re.compile(r'^TwentyFiveGigabitEthernet', re.IGNORECASE), 'Twe'),
    (re.compile(r'^TenGigabitEthernet', re.IGNORECASE), 'Te'),
    (re.compile(r'^GigabitEthernet', re.IGNORECASE), 'Gi'),
    (re.compile(r'^FastEthernet', re.IGNORECASE), 'Fa'),
    (re.compile(r'^Ethernet', re.IGNORECASE), 'Et'),
    (re.compile(r'^Loopback', re.IGNORECASE), 'Lo'),
    (re.compile(r'^Vlan', re.IGNORECASE), 'Vl'),
    (re.compile(r'^Management', re.IGNORECASE), 'Ma'),
    (re.compile(r'^Port-Channel', re.IGNORECASE), 'Po'),
]


def abbreviate_interface_name(name: str) -> str:
    for pattern, abbrev in _INTERFACE_ABBREV:
        abbreviated, n = pattern.subn(abbrev, name, count=1)
        if n:
            return abbreviated
    return name


IMAGE_DIR = Path(settings.STATIC_ROOT) / "nautobot_topology_views/img"
CONF_IMAGE_DIR: Path = Path(settings.STATIC_ROOT) / settings.PLUGINS_CONFIG[
    "nautobot_topology_views"
]["static_image_directory"].removeprefix("/")


def image_static_url(path: Path) -> str:
    return static(
        str(path.relative_to(Path(settings.STATIC_ROOT)))
    )


def get_image_from_url(url: str) -> str:
    if sys.version_info >= (3,9,0):
        return url.removeprefix(settings.STATIC_URL)
    else:
        if url.startswith(settings.STATIC_URL):
            url_new = url[len(settings.STATIC_URL):]
            return url_new
        else:
            return url


IMAGE_FILETYPES = (
    "apng",
    "avif",
    "bmp",
    "cur",
    "gif",
    "ico",
    "jfif",
    "jpeg",
    "jpg",
    "pjp",
    "pjpeg",
    "png",
    "svg",
    "webp",
)


def find_image_in_dir(glob: str, dir: Path):
    return next(
        (f for f in dir.glob(f"{glob}.*") if f.suffix.lstrip(".") in IMAGE_FILETYPES),
        None,
    )


@lru_cache(maxsize=50)
def find_image_url(glob: str, dir: Path = CONF_IMAGE_DIR):
    """
    will attempt to find a file that matches glob in given directory with any file extension,
    otherwise will try to find a `role-unknown` image

    returns static file url
    """
    if file := find_image_in_dir(glob, dir):
        return image_static_url(file)

    if glob != "role-unknown" and (file := find_image_in_dir("role-unknown", dir)):
        return image_static_url(file)

    if dir != IMAGE_DIR and (file := find_image_in_dir("role-unknown", IMAGE_DIR)):
        return image_static_url(file)

    return ""


@dataclass
class RoleData:
    slug: str
    name: str


def get_model_slug(model: Type[Model]):
    return camel_case_to_spaces(model.__name__).replace(" ", "-")


def get_model_role(model: Type[Model]) -> RoleData:
    return RoleData(
        slug=get_model_slug(model),
        name=re_camel_case.sub(r" \1", model.__name__),
    )


@dataclass
class TopologyQuerySettings:
    filter_id: str = ""
    ignore_cable_type: list[str] = field(default_factory=list)
    save_coords: bool = False
    show_unconnected: bool = False
    show_power: bool = False
    show_circuit: bool = False
    show_logical_connections: bool = False
    show_single_cable_logical_conns: bool = False
    show_cables: bool = False
    show_wireless: bool = False
    group_sites: bool = False
    group_locations: bool = False
    group_racks: bool = False
    group_virtualchassis: bool = False
    group: str = ""
    show_neighbors: bool = False
    straight_cables: bool = False
    draw_termination_labels: bool = False
    draw_cable_labels: bool = False
    grid_size: int | list[str] = 0
    node_label_items: list[str] = field(default_factory=list)
    show_virtual_machines: bool = False

    def as_topology_kwargs(self):
        return {
            "ignore_cable_type": self.ignore_cable_type,
            "save_coords": self.save_coords,
            "show_unconnected": self.show_unconnected,
            "show_cables": self.show_cables,
            "show_logical_connections": self.show_logical_connections,
            "show_single_cable_logical_conns": self.show_single_cable_logical_conns,
            "show_neighbors": self.show_neighbors,
            "show_circuit": self.show_circuit,
            "show_power": self.show_power,
            "show_wireless": self.show_wireless,
            "show_virtual_machines": self.show_virtual_machines,
            "group_sites": self.group_sites,
            "group_locations": self.group_locations,
            "group_racks": self.group_racks,
            "group_virtualchassis": self.group_virtualchassis,
            "group_id": self.group or "default",
            "straight_cables": self.straight_cables,
            "draw_termination_labels": self.draw_termination_labels,
            "draw_cable_labels": self.draw_cable_labels,
            "grid_size": self.grid_size,
            "node_label_items": self.node_label_items,
        }


def _stored_list(value: str) -> list[str]:
    values = value.translate({ord(character): None for character in "[]'"}).split(", ")
    return [] if values == [""] else values


def get_query_settings(request, individual_options=None) -> TopologyQuerySettings:
    if not request.GET and individual_options is not None:
        query_settings = TopologyQuerySettings(
            ignore_cable_type=_stored_list(individual_options.ignore_cable_type),
            save_coords=individual_options.save_coords,
            show_unconnected=individual_options.show_unconnected,
            show_power=individual_options.show_power,
            show_circuit=individual_options.show_circuit,
            show_logical_connections=individual_options.show_logical_connections,
            show_single_cable_logical_conns=individual_options.show_single_cable_logical_conns,
            show_cables=individual_options.show_cables,
            show_wireless=individual_options.show_wireless,
            group_sites=individual_options.group_sites,
            group_locations=individual_options.group_locations,
            group_racks=individual_options.group_racks,
            group_virtualchassis=individual_options.group_virtualchassis,
            show_neighbors=individual_options.show_neighbors,
            straight_cables=individual_options.straight_cables,
            draw_termination_labels=individual_options.draw_termination_labels,
            draw_cable_labels=individual_options.draw_cable_labels,
            grid_size=individual_options.grid_size,
            node_label_items=_stored_list(individual_options.node_label_items),
            show_virtual_machines=individual_options.show_virtual_machines,
        )
    else:
        query_settings = TopologyQuerySettings(
            filter_id=request.GET.get("filter_id", ""),
            ignore_cable_type=request.GET.getlist("ignore_cable_type"),
            save_coords=request.GET.get("save_coords") == "True",
            show_unconnected=request.GET.get("show_unconnected") == "True",
            show_power=request.GET.get("show_power") == "True",
            show_circuit=request.GET.get("show_circuit") == "True",
            show_logical_connections=request.GET.get("show_logical_connections") == "True",
            show_single_cable_logical_conns=request.GET.get("show_single_cable_logical_conns") == "True",
            show_cables=request.GET.get("show_cables") == "True",
            show_wireless=request.GET.get("show_wireless") == "True",
            group_sites=request.GET.get("group_sites") == "True",
            group_locations=request.GET.get("group_locations") == "True",
            group_racks=request.GET.get("group_racks") == "True",
            group_virtualchassis=request.GET.get("group_virtualchassis") == "True",
            group=request.GET.get("group", ""),
            show_neighbors=request.GET.get("show_neighbors") == "True",
            straight_cables=request.GET.get("straight_cables") == "True",
            draw_termination_labels=request.GET.get("draw_termination_labels") == "True",
            draw_cable_labels=request.GET.get("draw_cable_labels") == "True",
            grid_size=request.GET.getlist("grid_size") if "grid_size" in request.GET else 0,
            node_label_items=request.GET.getlist("node_label_items"),
            show_virtual_machines=request.GET.get("show_virtual_machines") == "True",
        )

    plugin_settings = settings.PLUGINS_CONFIG["nautobot_topology_views"]
    if query_settings.save_coords and not plugin_settings["allow_coordinates_saving"]:
        query_settings.save_coords = False
        messages.warning(request, "Coordinate saving not allowed. Setting has been overridden")
    elif plugin_settings["always_save_coordinates"]:
        query_settings.save_coords = True

    return query_settings


class LinePattern:
    wireless = [2, 10, 2, 10]
    power = [5, 5, 3, 3]
    logical = [1, 10, 1, 10]
    virtual = [8, 4, 2, 4]


def export_data_to_xml(data: dict):
    if data is None:
        return ''

    # static xml header
    doc = xml.dom.minidom.Document()
    mxfile = doc.createElement('mxfile')
    mxfile.setAttribute('host', 'app.diagrams.net')
    mxfile.setAttribute('type', 'device')
    diagram = doc.createElement('diagram')
    diagram.setAttribute('name', 'topology')
    diagram.setAttribute('id', 'someid')

    doc.appendChild(mxfile)
    mxfile.appendChild(diagram)

    # mxGraphModel
    mxgraphmodel = doc.createElement('mxGraphModel')
    mxgraphmodel.setAttribute('dx', '0')
    mxgraphmodel.setAttribute('dy', '0')
    mxgraphmodel.setAttribute('grid', '0')
    mxgraphmodel.setAttribute('guides', '1')
    mxgraphmodel.setAttribute('tooltips', '1')
    mxgraphmodel.setAttribute('connect', '1')
    mxgraphmodel.setAttribute('arrows', '1')
    mxgraphmodel.setAttribute('fold', '1')
    mxgraphmodel.setAttribute('page', '1')
    mxgraphmodel.setAttribute('pageScale', '1')
    mxgraphmodel.setAttribute('pageWidth', '827')
    mxgraphmodel.setAttribute('pageHeight', '1169')
    mxgraphmodel.setAttribute('background', 'none')
    mxgraphmodel.setAttribute('math', '0')
    mxgraphmodel.setAttribute('shadow', '0')

    diagram.appendChild(mxgraphmodel)

    # root
    root = doc.createElement('root')

    mxgraphmodel.appendChild(root)

    # mxCells
    # header
    mxcell = doc.createElement('mxCell')
    mxcell.setAttribute('id', '0')
    root.appendChild(mxcell)
    mxcell = doc.createElement('mxCell')
    mxcell.setAttribute('id', '1')
    mxcell.setAttribute('parent', '0')
    root.appendChild(mxcell)

    # edges
    for edge in data['edges']:
        dashes = ''
        if 'dashes' in edge:
            if edge['dashes'] == LinePattern().wireless:
                dashes = 'dashed=1;dashPattern=3 6;'
            if edge['dashes'] == LinePattern().power:
                dashes = 'dashed=1;dashPattern=6 6;'
            if edge['dashes'] == LinePattern().logical:
                dashes = 'dashed=1;dashPattern=1 4;strokeWidth=2;'
            if edge['dashes'] == LinePattern().virtual:
                dashes = 'dashed=1;dashPattern=8 4 2 4;'

        mxcell = doc.createElement('mxCell')
        mxcell.setAttribute('id', 'edge_' + str(edge['id']))
        mxcell.setAttribute('style', 'rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=none;endFill=0;strokeColor=' + edge['color'] + ';' + dashes)
        mxcell.setAttribute('edge', '1')
        mxcell.setAttribute('parent', '1')
        mxcell.setAttribute('source', 'node_' + str(edge['from']))
        mxcell.setAttribute('target', 'node_' + str(edge['to']))

        root.appendChild(mxcell)

        mxgeometry = doc.createElement('mxGeometry')
        mxgeometry.setAttribute('relative', '1')
        mxgeometry.setAttribute('as', 'geometry')

        mxcell.appendChild(mxgeometry)

    # nodes
    noPositionX = 0
    noPositionY = 1000
    for node in data['nodes']:
        with open(settings.STATIC_ROOT + '/' + get_image_from_url(node['image']), "rb") as img:
            svg = base64.b64encode(img.read()).decode('utf-8')
        mxcell = doc.createElement('mxCell')
        mxcell.setAttribute('id', 'node_' + str(node['id']))
        mxcell.setAttribute('value', str(node['label']))
        mxcell.setAttribute('style', 'shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;image=data:image/svg+xml,' + svg + ';perimeter=elippsePerimeter;fontSize=10;strokeWidth=1;fontColor=#000000;')
        mxcell.setAttribute('vertex', '1')
        mxcell.setAttribute('parent', '1')

        root.appendChild(mxcell)

        mxgeometry = doc.createElement('mxGeometry')
        # Check if x and y values are stored in the database and set pseudo
        # coordinates if not. Otherwise icons will not be exported / KeyError is raised
        if 'x' in node:
            mxgeometry.setAttribute('x', str(node['x']))
        else:
            # Set next pseudo coordinates
            if noPositionX > 2500:
                noPositionX = 100
                noPositionY = noPositionY + 100
            else:
                noPositionX = noPositionX + 100

            mxgeometry.setAttribute('x', str(noPositionX))
        if 'y' in node:
            mxgeometry.setAttribute('y', str(node['y']))
        else:
            mxgeometry.setAttribute('y', str(noPositionY))

        mxgeometry.setAttribute('width', '50')
        mxgeometry.setAttribute('height', '50')
        mxgeometry.setAttribute('as', 'geometry')

        mxcell.appendChild(mxgeometry)

    # Place a warning if one or more icons are misplaced because of missing coordinates
    if noPositionX > 0:
        mxcell = doc.createElement('mxCell')
        mxcell.setAttribute('id', 'noPositionWarning')
        mxcell.setAttribute('value', 'One or more icons are misplaced. This happens if no coordinates are stored for a device. Turn on coordinates saving and make sure to drag all icons in the topology to a specific position before exporting to XML.')
        mxcell.setAttribute('style', 'text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontColor=#FF0000;fontStyle=0;fontSize=35;labelBackgroundColor=#FFFF99;labelBorderColor=none;strokeWidth=20;')
        mxcell.setAttribute('vertex', '1')
        mxcell.setAttribute('parent', '1')

        root.appendChild(mxcell)

        mxgeometry = doc.createElement('mxGeometry')
        mxgeometry.setAttribute('x', '0')
        mxgeometry.setAttribute('y', '0')
        mxgeometry.setAttribute('width', '870')
        mxgeometry.setAttribute('height', '100')
        mxgeometry.setAttribute('as', 'geometry')

        mxcell.appendChild(mxgeometry)

    # debug output
    # print(doc.toprettyxml())

    return doc.toxml(encoding='UTF-8')
