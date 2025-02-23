
from maya import cmds

import pyblish.api
from ayon_core.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateGLSLPlugin(pyblish.api.InstancePlugin):
    """
    Validate if the asset uses GLSL Shader
    """

    order = ValidateContentsOrder + 0.15
    families = ['gltf']
    hosts = ['maya']
    label = 'maya2glTF plugin'
    actions = [RepairAction]

    def process(self, instance):
        if not cmds.pluginInfo("maya2glTF", query=True, loaded=True):
            raise PublishValidationError("maya2glTF is not loaded")

    @classmethod
    def repair(cls, instance):
        """
        Repair instance by enabling the plugin
        """
        return cmds.loadPlugin("maya2glTF", quiet=True)
