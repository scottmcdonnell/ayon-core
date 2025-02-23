import pyblish.api

from maya import cmds

import ayon_core.hosts.maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError
)



class ValidateVrayProxyMembers(pyblish.api.InstancePlugin):
    """Validate whether the V-Ray Proxy instance has shape members"""

    order = pyblish.api.ValidatorOrder
    label = 'VRay Proxy Members'
    hosts = ['maya']
    families = ['vrayproxy']
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError("'%s' is invalid VRay Proxy for "
                               "export!" % instance.name)

    @classmethod
    def get_invalid(cls, instance):

        shapes = cmds.ls(instance,
                         shapes=True,
                         noIntermediate=True,
                         long=True)

        if not shapes:
            cls.log.error("'%s' contains no shapes." % instance.name)

            # Return the instance itself
            return [instance.name]
