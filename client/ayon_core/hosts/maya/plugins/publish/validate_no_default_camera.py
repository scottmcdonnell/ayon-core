from maya import cmds

import pyblish.api
import ayon_core.hosts.maya.api.action
from ayon_core.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError
)


def _as_report_list(values, prefix="- ", suffix="\n"):
    """Return list as bullet point list for a report"""
    if not values:
        return ""
    return prefix + (suffix + prefix).join(values)


class ValidateNoDefaultCameras(pyblish.api.InstancePlugin):
    """Ensure no default (startup) cameras are in the instance.

    This might be unnecessary. In the past there were some issues with
    referencing/importing files that contained the start up cameras overriding
    settings when being loaded and sometimes being skipped.
    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ['camera']
    label = "No Default Cameras"
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):
        cameras = cmds.ls(instance, type='camera', long=True)
        return [cam for cam in cameras if
                cmds.camera(cam, query=True, startupCamera=True)]

    def process(self, instance):
        """Process all the cameras in the instance"""
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Default cameras found:\n\n{0}".format(
                    _as_report_list(sorted(invalid))
                ),
                title="Default cameras"
            )
