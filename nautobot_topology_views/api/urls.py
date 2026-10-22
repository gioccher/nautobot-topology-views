from nautobot.apps.api import OrderedDefaultRouter

from nautobot_topology_views.api import views

router = OrderedDefaultRouter()

router.register("save-coords", views.SaveCoordsViewSet)
router.register("images", views.SaveRoleImageViewSet)
router.register("xml-export", views.ExportTopoToXML, "xml-export")
router.register("coordinate-groups", views.CoordinateGroupViewSet)
router.register("coordinate", views.CoordinateViewSet)
router.register("circuitcoordinate", views.CircuitCoordinateViewSet)
router.register("powerpanelcoordinate", views.PowerPanelCoordinateViewSet)
router.register("powerfeedcoordinate", views.PowerFeedCoordinateViewSet)
router.register("virtualmachinecoordinate", views.VirtualMachineCoordinateViewSet)

urlpatterns = router.urls
