import pyblish.api
import ayon_core.hosts.maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError
)

class ValidateAssemblyNamespaces(pyblish.api.InstancePlugin):
    """Ensure namespaces are not nested

    In the outliner an item in a normal namespace looks as following:
        props_desk_01_:modelDefault

    Any namespace which diverts from that is illegal, example of an illegal
    namespace:
        room_study_01_:props_desk_01_:modelDefault

    """

    label = "Validate Assembly Namespaces"
    order = pyblish.api.ValidatorOrder
    families = ["assembly"]
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction]

    def process(self, instance):

        self.log.debug("Checking namespace for %s" % instance.name)
        if self.get_invalid(instance):
            raise PublishValidationError("Nested namespaces found")

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = []
        for item in cmds.ls(instance):
            item_parts = item.split("|", 1)[0].rsplit(":")
            if len(item_parts[:-1]) > 1:
                invalid.append(item)

        return invalid
