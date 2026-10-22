# Virtual machines on the topology: a coordinate model for VM nodes and the
# per-user "show virtual machines" option.

import django.core.serializers.json
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.extras.models.mixins
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0142_remove_scheduledjob_approval_required"),
        ("virtualization", "0030_alter_virtualmachine_local_config_context_data_owner_content_type_and_more"),
        ("nautobot_topology_views", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="individualoptions",
            name="show_virtual_machines",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="VirtualMachineCoordinate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "_custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
                ),
                ("x", models.IntegerField(help_text='X-coordinate of the virtual machine (horizontal) on the canvas. ' 'Smaller values correspond to a position further to the left on the monitor.')),
                ("y", models.IntegerField(help_text='Y-coordinate of the virtual machine (vertical) on the canvas. ' 'Smaller values correspond to a position further up on the monitor.')),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="virtualization.virtualmachine"
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="nautobot_topology_views.coordinategroup"
                    ),
                ),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ["group", "device"],
                "unique_together": {("device", "group")},
            },
            bases=(
                nautobot.extras.models.mixins.DataComplianceModelMixin,
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
    ]
