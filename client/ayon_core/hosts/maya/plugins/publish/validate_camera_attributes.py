import pyblish.api
from maya import cmds

import ayon_core.hosts.maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError, ValidateContentsOrder)


class ValidateCameraAttributes(pyblish.api.InstancePlugin):
    """Validates Camera has no invalid attribute keys or values.

    The Alembic file format does not a specific subset of attributes as such
    we validate that no values are set there as the output will not match the
    current scene. For example the preScale, film offsets and film roll.

    """

    order = ValidateContentsOrder
    families = ['camera']
    hosts = ['maya']
    label = 'Camera Attributes'
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction]

    DEFAULTS = [
        ("filmFitOffset", 0.0),
        ("horizontalFilmOffset", 0.0),
        ("verticalFilmOffset", 0.0),
        ("preScale", 1.0),
        ("filmTranslateH", 0.0),
        ("filmTranslateV", 0.0),
        ("filmRollValue", 0.0)
    ]

    @classmethod
    def get_invalid(cls, instance):

        # get cameras
        members = instance.data['setMembers']
        shapes = cmds.ls(members, dag=True, shapes=True, long=True)
        cameras = cmds.ls(shapes, type='camera', long=True)

        invalid = set()
        for cam in cameras:

            for attr, default_value in cls.DEFAULTS:
                plug = "{}.{}".format(cam, attr)
                value = cmds.getAttr(plug)

                # Check if is default value
                if value != default_value:
                    cls.log.warning("Invalid attribute value: {0} "
                                    "(should be: {1}))".format(plug,
                                                               default_value))
                    invalid.add(cam)

                if cmds.listConnections(plug, source=True, destination=False):
                    # TODO: Validate correctly whether value always correct
                    cls.log.warning("%s has incoming connections, validation "
                                    "is unpredictable." % plug)

        return list(invalid)

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Invalid camera attributes: {}".format(invalid))
