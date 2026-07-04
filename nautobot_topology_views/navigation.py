"""Navigation menu items for Nautobot Topology Views."""

from nautobot.apps.ui import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuImportButton,
    NavMenuItem,
    NavMenuTab,
)

menu_items = (
    NavMenuTab(
        name="Topology Views",
        weight=1000,
        groups=(
            NavMenuGroup(
                name="Topology",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:home",
                        name="Topology",
                        permissions=["dcim.view_location", "dcim.view_device"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Coordinates",
                weight=200,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:coordinategroup_list",
                        name="Coordinate Groups",
                        permissions=["nautobot_topology_views.view_coordinategroup"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_topology_views:coordinategroup_add",
                                permissions=["nautobot_topology_views.add_coordinategroup"],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobot_topology_views:coordinategroup_import",
                                permissions=["nautobot_topology_views.add_coordinategroup"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:coordinate_list",
                        name="Device Coordinates",
                        permissions=["nautobot_topology_views.view_coordinate"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_topology_views:coordinate_add",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobot_topology_views:coordinate_import",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:powerfeedcoordinate_list",
                        name="Power Feed Coords",
                        permissions=["nautobot_topology_views.view_coordinate"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_topology_views:powerfeedcoordinate_add",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobot_topology_views:powerfeedcoordinate_import",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:powerpanelcoordinate_list",
                        name="Power Panel Coords",
                        permissions=["nautobot_topology_views.view_coordinate"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_topology_views:powerpanelcoordinate_add",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobot_topology_views:powerpanelcoordinate_import",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:circuitcoordinate_list",
                        name="Circuit Coordinates",
                        permissions=["nautobot_topology_views.view_coordinate"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_topology_views:circuitcoordinate_add",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobot_topology_views:circuitcoordinate_import",
                                permissions=["nautobot_topology_views.add_coordinate"],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Preferences",
                weight=300,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:images",
                        name="Icons",
                        permissions=["dcim.view_location", "extras.view_role"],
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_topology_views:individualoptions",
                        name="Default Options",
                        permissions=["nautobot_topology_views.change_individualoptions"],
                    ),
                ),
            ),
        ),
    ),
)
