from pathlib import Path
from typing import Optional

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from nautobot.apps.models import PrimaryModel
from nautobot.circuits.models import Circuit
from nautobot.dcim.models import Device, PowerFeed, PowerPanel
from nautobot.extras.models import ChangeLoggedModel, Role, Tag
from nautobot.virtualization.models import VirtualMachine

from nautobot_topology_views.choices import NodeLabelItems
from nautobot_topology_views.utils import (
    CONF_IMAGE_DIR,
    IMAGE_DIR,
    RoleData,
    find_image_url,
    get_model_role,
    image_static_url,
)


class RoleImage(ChangeLoggedModel):
    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    objects: "models.Manager[RoleImage]"

    image = models.CharField("Path within the nautobot static directory", max_length=255)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField(null=True, blank=True)

    __role: Optional["RoleData"] = None

    @property
    def role_data(self) -> "RoleData":
        if self.__role:
            return self.__role

        model_class = self.content_type.model_class()

        if not model_class:
            raise ValueError(f"Invalid content type: {self.content_type}")

        if model_class == Role:
            device_role: Role = Role.objects.get(pk=self.object_id)
            self.__role = RoleData(slug=device_role.name, name=device_role.name)
            return self.__role

        self.__role = get_model_role(model_class)
        return self.__role

    def __str__(self):
        return f"{self.role_data} - {self.image}"

    def get_image(self) -> Path:
        """Get Icon

        returns the model's image's absolute path in the filesystem
        raises ValueError if the file cannot be found
        """
        path = Path(settings.STATIC_ROOT) / self.image

        if not path.exists():
            raise ValueError(f"{self.role_data} path '{path}' does not exists")

        return path

    def get_default_image(self, dir: Path = CONF_IMAGE_DIR):
        """Get default image

        will attempt to find image in given directory with any file extension,
        otherwise will try to find a `role-unknown` image

        fallback is `STATIC_ROOT/nautobot_topology_views/img/role-unknown.png`
        """
        if url := find_image_url(self.role_data.slug, dir):
            return url

        # fallback to default role unknown image
        return image_static_url(IMAGE_DIR / "role-unknown.png")

    def get_image_url(self, dir: Path = CONF_IMAGE_DIR) -> str:
        try:
            self.get_image()
        except ValueError:
            return self.get_default_image(dir)
        return static(str(self.image))

class CoordinateGroup(PrimaryModel):
    """
    A coordinate group is used to display the topology for a particular group.
    This allows different visualizations with the same devices.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.CharField(
        max_length=255,
        blank = True,
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:nautobot_topology_views:coordinategroup', args=[self.pk])

class Coordinate(PrimaryModel):
    """
    Coordinates are being used to place devices in a topology view onto a certain
    position. Devices belong to one or more coordinate groups. They have to
    be unique together.
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    group = models.ForeignKey(CoordinateGroup, on_delete=models.CASCADE)

    x = models.IntegerField(
        help_text='X-coordinate of the device (horizontal) on the canvas. '
            'Smaller values correspond to a position further to the left on the monitor.',
    )
    y = models.IntegerField(
        help_text='Y-coordinate of the device (vertical) on the canvas. '
            'Smaller values correspond to a position further up on the monitor.',
    )

    def get_or_create_default_group(group_id):
        # Default group named "default" must always exist in order to make sure
        # that coordinate values can be stored even if no coordinate group has been
        # selected. The default group will be added automatically if it does not exist.
        try:
            if CoordinateGroup.objects.filter(name="default"):
                group = CoordinateGroup.objects.get(name="default")
                group_id = group.pk
            else:
                group = CoordinateGroup(
                    name="default",
                    description="Automatically generated default group. If you delete "
                        "this group, all default coordinates are gone for good but "
                        "the group itself will be re-created."
                )
                group.save()
                group_id = group.pk
        except:
            return False
        return group_id

    class Meta:
        ordering = ['group', 'device']
        unique_together = ('device', 'group')

    def __str__(self):
        return f'{self.x};{self.y}'

    def get_absolute_url(self):
        return reverse('plugins:nautobot_topology_views:coordinate', args=[self.pk])

class CircuitCoordinate(PrimaryModel):
    """
    Coordinates are being used to place devices in a topology view onto a certain
    position. Devices belong to one or more coordinate groups. They have to
    be unique together.
    """
    device = models.ForeignKey(Circuit, on_delete=models.CASCADE)
    group = models.ForeignKey(CoordinateGroup, on_delete=models.CASCADE)

    x = models.IntegerField(
        help_text='X-coordinate of the device (horizontal) on the canvas. '
            'Smaller values correspond to a position further to the left on the monitor.',
    )
    y = models.IntegerField(
        help_text='Y-coordinate of the device (vertical) on the canvas. '
            'Smaller values correspond to a position further up on the monitor.',
    )

    def get_or_create_default_group(group_id):
        # Default group named "default" must always exist in order to make sure
        # that coordinate values can be stored even if no coordinate group has been
        # selected. The default group will be added automatically if it does not exist.
        try:
            if CoordinateGroup.objects.filter(name="default"):
                group = CoordinateGroup.objects.get(name="default")
                group_id = group.pk
            else:
                group = CoordinateGroup(
                    name="default",
                    description="Automatically generated default group. If you delete "
                        "this group, all default coordinates are gone for good but "
                        "the group itself will be re-created."
                )
                group.save()
                group_id = group.pk
        except:
            return False
        return group_id

    class Meta:
        ordering = ['group', 'device']
        unique_together = ('device', 'group')

    def __str__(self):
        return f'{self.x};{self.y}'

    def get_absolute_url(self):
        return reverse('plugins:nautobot_topology_views:circuitcoordinate', args=[self.pk])

class PowerPanelCoordinate(PrimaryModel):
    """
    Coordinates are being used to place devices in a topology view onto a certain
    position. Devices belong to one or more coordinate groups. They have to
    be unique together.
    """
    device = models.ForeignKey(PowerPanel, on_delete=models.CASCADE)
    group = models.ForeignKey(CoordinateGroup, on_delete=models.CASCADE)

    x = models.IntegerField(
        help_text='X-coordinate of the device (horizontal) on the canvas. '
            'Smaller values correspond to a position further to the left on the monitor.',
    )
    y = models.IntegerField(
        help_text='Y-coordinate of the device (vertical) on the canvas. '
            'Smaller values correspond to a position further up on the monitor.',
    )

    def get_or_create_default_group(group_id):
        # Default group named "default" must always exist in order to make sure
        # that coordinate values can be stored even if no coordinate group has been
        # selected. The default group will be added automatically if it does not exist.
        try:
            if CoordinateGroup.objects.filter(name="default"):
                group = CoordinateGroup.objects.get(name="default")
                group_id = group.pk
            else:
                group = CoordinateGroup(
                    name="default",
                    description="Automatically generated default group. If you delete "
                        "this group, all default coordinates are gone for good but "
                        "the group itself will be re-created."
                )
                group.save()
                group_id = group.pk
        except:
            return False
        return group_id

    class Meta:
        ordering = ['group', 'device']
        unique_together = ('device', 'group')

    def __str__(self):
        return f'{self.x};{self.y}'

    def get_absolute_url(self):
        return reverse('plugins:nautobot_topology_views:powerpanelcoordinate', args=[self.pk])

class PowerFeedCoordinate(PrimaryModel):
    """
    Coordinates are being used to place devices in a topology view onto a certain
    position. Devices belong to one or more coordinate groups. They have to
    be unique together.
    """
    device = models.ForeignKey(PowerFeed, on_delete=models.CASCADE)
    group = models.ForeignKey(CoordinateGroup, on_delete=models.CASCADE)

    x = models.IntegerField(
        help_text='X-coordinate of the device (horizontal) on the canvas. '
            'Smaller values correspond to a position further to the left on the monitor.',
    )
    y = models.IntegerField(
        help_text='Y-coordinate of the device (vertical) on the canvas. '
            'Smaller values correspond to a position further up on the monitor.',
    )

    def get_or_create_default_group(group_id):
        # Default group named "default" must always exist in order to make sure
        # that coordinate values can be stored even if no coordinate group has been
        # selected. The default group will be added automatically if it does not exist.
        try:
            if CoordinateGroup.objects.filter(name="default"):
                group = CoordinateGroup.objects.get(name="default")
                group_id = group.pk
            else:
                group = CoordinateGroup(
                    name="default",
                    description="Automatically generated default group. If you delete "
                        "this group, all default coordinates are gone for good but "
                        "the group itself will be re-created."
                )
                group.save()
                group_id = group.pk
        except:
            return False
        return group_id

    class Meta:
        ordering = ['group', 'device']
        unique_together = ('device', 'group')

    def __str__(self):
        return f'{self.x};{self.y}'

    def get_absolute_url(self):
        return reverse('plugins:nautobot_topology_views:powerfeedcoordinate', args=[self.pk])

class VirtualMachineCoordinate(PrimaryModel):
    """
    Coordinates for virtual machines. A VM is drawn hanging off the hosts of its
    cluster and, like a device, keeps one position per coordinate group. The FK
    is named `device` so the save-coords path and the tables treat every node
    kind the same way.
    """
    device = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE)
    group = models.ForeignKey(CoordinateGroup, on_delete=models.CASCADE)

    x = models.IntegerField(
        help_text='X-coordinate of the virtual machine (horizontal) on the canvas. '
            'Smaller values correspond to a position further to the left on the monitor.',
    )
    y = models.IntegerField(
        help_text='Y-coordinate of the virtual machine (vertical) on the canvas. '
            'Smaller values correspond to a position further up on the monitor.',
    )

    def get_or_create_default_group(group_id):
        # Default group named "default" must always exist in order to make sure
        # that coordinate values can be stored even if no coordinate group has been
        # selected. The default group will be added automatically if it does not exist.
        try:
            if CoordinateGroup.objects.filter(name="default"):
                group = CoordinateGroup.objects.get(name="default")
                group_id = group.pk
            else:
                group = CoordinateGroup(
                    name="default",
                    description="Automatically generated default group. If you delete "
                        "this group, all default coordinates are gone for good but "
                        "the group itself will be re-created."
                )
                group.save()
                group_id = group.pk
        except:
            return False
        return group_id

    class Meta:
        ordering = ['group', 'device']
        unique_together = ('device', 'group')

    def __str__(self):
        return f'{self.x};{self.y}'

    def get_absolute_url(self):
        return reverse('plugins:nautobot_topology_views:virtualmachinecoordinate', args=[self.pk])

class IndividualOptions(PrimaryModel):
    CHOICES = (
        ('interface', 'interface'),
        ('frontport', 'frontport'),
        ('rearport', 'rearport'),
        ('poweroutlet', 'poweroutlet'),
        ('powerport', 'powerport'),
        ('consoleport', 'consoleport'),
        ('consoleserverport', 'consoleserverport'),
    )

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        unique=True,
        related_name='+',
    )
    ignore_cable_type = models.CharField(
        max_length = 255,
        blank = True,
    )
    preselected_device_roles = models.ManyToManyField(
        to='extras.Role',
        related_name='+',
        blank=True,
        db_table='nautobot_topology_views_individualoptions_preselected_device',
    )
    preselected_tags = models.ManyToManyField(
        to='extras.Tag',
        related_name='+',
        blank=True,
        db_table='nautobot_topology_views_individualoptions_preselected_tag',
    )
    save_coords = models.BooleanField(
        default=False
    )
    show_unconnected = models.BooleanField(
        default=False
    )
    show_cables = models.BooleanField(
        default=False
    )
    show_logical_connections = models.BooleanField(
        default=False
    )
    show_single_cable_logical_conns = models.BooleanField(
        default=False
    )
    show_neighbors = models.BooleanField(
        default=False
    )
    show_circuit = models.BooleanField(
        default=False
    )
    show_power = models.BooleanField(
        default=False
    )
    show_wireless = models.BooleanField(
        default=False
    )
    show_virtual_machines = models.BooleanField(
        default=False
    )
    group_sites = models.BooleanField(
        default=False
    )
    group_locations = models.BooleanField(
        default=False
    )
    group_racks = models.BooleanField(
        default=False
    )
    group_virtualchassis = models.BooleanField(
        default=False
    )
    draw_default_layout = models.BooleanField(
        default=False
    )
    straight_cables = models.BooleanField(
        default=False
    )
    draw_termination_labels = models.BooleanField(
        default=False
    )
    draw_cable_labels = models.BooleanField(
        default=False
    )
    grid_size = models.PositiveSmallIntegerField(
        default=0
    )
    node_label_items = models.CharField(
        max_length=255,
        blank=True
    )

    def __str___(self):
        return f"{self.user}"
