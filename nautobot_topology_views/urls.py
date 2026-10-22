from django.urls import path
from django.views.generic.base import RedirectView
from nautobot.extras.views import ObjectChangeLogView

from . import models, views

# Define a list of URL patterns to be imported by Nautobot. Each pattern maps a URL to
# a specific view so that it can be accessed by users.
urlpatterns = (
    path("", RedirectView.as_view(url="topology/", permanent=True), name="index"),
    path("topology/", views.TopologyHomeView.as_view(), name="home"),
    path("images/", views.TopologyImagesView.as_view(), name="images"),
    path("individualoptions/", views.TopologyIndividualOptionsView.as_view(), name="individualoptions"),

    # Coordinate Group
    path("coordinate-groups/", views.CoordinateGroupListView.as_view(), name="coordinategroup_list"),
    path("coordinate-groups/add/", views.CoordinateGroupAddView.as_view(), name="coordinategroup_add"),
    path('coordinate-groups/import/', views.CoordinateGroupBulkImportView.as_view(), name='coordinategroup_import'),
    path("coordinate-groups/<uuid:pk>/", views.CoordinateGroupView.as_view(), name="coordinategroup"),
    path("coordinate-groups/<uuid:pk>/edit/", views.CoordinateGroupEditView.as_view(), name="coordinategroup_edit"),
    path("coordinate-groups/<uuid:pk>/delete/", views.CoordinateGroupDeleteView.as_view(), name="coordinategroup_delete"),
    path("coordinate-groups/<uuid:pk>/changelog/", ObjectChangeLogView.as_view(), name="coordinategroup_changelog", kwargs={'model': models.CoordinateGroup}),

    # Circuit Coordinate
    path("circuitcoordinate/", views.CircuitCoordinateListView.as_view(), name="circuitcoordinate_list"),
    path("circuitcoordinate/add/", views.CircuitCoordinateAddView.as_view(), name="circuitcoordinate_add"),
    path('circuitcoordinate/import/', views.CircuitCoordinateBulkImportView.as_view(), name='circuitcoordinate_import'),
    path("circuitcoordinate/<uuid:pk>/", views.CircuitCoordinateView.as_view(), name="circuitcoordinate"),
    path("circuitcoordinate/<uuid:pk>/edit/", views.CircuitCoordinateEditView.as_view(), name="circuitcoordinate_edit"),
    path("circuitcoordinate/<uuid:pk>/delete/", views.CircuitCoordinateDeleteView.as_view(), name="circuitcoordinate_delete"),
    path("circuitcoordinate/<uuid:pk>/changelog/", ObjectChangeLogView.as_view(), name="circuitcoordinate_changelog", kwargs={'model': models.CircuitCoordinate}),

    # Power Panel Coordinate
    path("powerpanelcoordinate/", views.PowerPanelCoordinateListView.as_view(), name="powerpanelcoordinate_list"),
    path("powerpanelcoordinate/add/", views.PowerPanelCoordinateAddView.as_view(), name="powerpanelcoordinate_add"),
    path('powerpanelcoordinate/import/', views.PowerPanelCoordinateBulkImportView.as_view(), name='powerpanelcoordinate_import'),
    path("powerpanelcoordinate/<uuid:pk>/", views.PowerPanelCoordinateView.as_view(), name="powerpanelcoordinate"),
    path("powerpanelcoordinate/<uuid:pk>/edit/", views.PowerPanelCoordinateEditView.as_view(), name="powerpanelcoordinate_edit"),
    path("powerpanelcoordinate/<uuid:pk>/delete/", views.PowerPanelCoordinateDeleteView.as_view(), name="powerpanelcoordinate_delete"),
    path("powerpanelcoordinate/<uuid:pk>/changelog/", ObjectChangeLogView.as_view(), name="powerpanelcoordinate_changelog", kwargs={'model': models.PowerPanelCoordinate}),

    # Power Feed Coordinate
    path("powerfeedcoordinate/", views.PowerFeedCoordinateListView.as_view(), name="powerfeedcoordinate_list"),
    path("powerfeedcoordinate/add/", views.PowerFeedCoordinateAddView.as_view(), name="powerfeedcoordinate_add"),
    path('powerfeedcoordinate/import/', views.PowerFeedCoordinateBulkImportView.as_view(), name='powerfeedcoordinate_import'),
    path("powerfeedcoordinate/<uuid:pk>/", views.PowerFeedCoordinateView.as_view(), name="powerfeedcoordinate"),
    path("powerfeedcoordinate/<uuid:pk>/edit/", views.PowerFeedCoordinateEditView.as_view(), name="powerfeedcoordinate_edit"),
    path("powerfeedcoordinate/<uuid:pk>/delete/", views.PowerFeedCoordinateDeleteView.as_view(), name="powerfeedcoordinate_delete"),
    path("powerfeedcoordinate/<uuid:pk>/changelog/", ObjectChangeLogView.as_view(), name="powerfeedcoordinate_changelog", kwargs={'model': models.PowerFeedCoordinate}),

    # Virtual Machine Coordinate
    path("virtualmachinecoordinate/", views.VirtualMachineCoordinateListView.as_view(), name="virtualmachinecoordinate_list"),
    path("virtualmachinecoordinate/add/", views.VirtualMachineCoordinateAddView.as_view(), name="virtualmachinecoordinate_add"),
    path('virtualmachinecoordinate/import/', views.VirtualMachineCoordinateBulkImportView.as_view(), name='virtualmachinecoordinate_import'),
    path("virtualmachinecoordinate/<uuid:pk>/", views.VirtualMachineCoordinateView.as_view(), name="virtualmachinecoordinate"),
    path("virtualmachinecoordinate/<uuid:pk>/edit/", views.VirtualMachineCoordinateEditView.as_view(), name="virtualmachinecoordinate_edit"),
    path("virtualmachinecoordinate/<uuid:pk>/delete/", views.VirtualMachineCoordinateDeleteView.as_view(), name="virtualmachinecoordinate_delete"),
    path("virtualmachinecoordinate/<uuid:pk>/changelog/", ObjectChangeLogView.as_view(), name="virtualmachinecoordinate_changelog", kwargs={'model': models.VirtualMachineCoordinate}),

    # Coordinate
    path("coordinate/", views.CoordinateListView.as_view(), name="coordinate_list"),
    path("coordinate/add/", views.CoordinateAddView.as_view(), name="coordinate_add"),
    path('coordinate/import/', views.CoordinateBulkImportView.as_view(), name='coordinate_import'),
    path("coordinate/<uuid:pk>/", views.CoordinateView.as_view(), name="coordinate"),
    path("coordinate/<uuid:pk>/edit/", views.CoordinateEditView.as_view(), name="coordinate_edit"),
    path("coordinate/<uuid:pk>/delete/", views.CoordinateDeleteView.as_view(), name="coordinate_delete"),
    path("coordinate/<uuid:pk>/changelog/", ObjectChangeLogView.as_view(), name="coordinate_changelog", kwargs={'model': models.Coordinate}),

    # Location topology tab
    path("location/<uuid:pk>/topology/", views.LocationTopologyView.as_view(), name="location_topology"),
)
