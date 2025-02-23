from maya import cmds

import pyblish.api
import ayon_core.hosts.maya.api.action
from ayon_core.hosts.maya.api import lib
from ayon_core.pipeline.publish import ValidateContentsOrder


class ValidateMeshNgons(pyblish.api.Validator):
    """Ensure that meshes don't have ngons

    Ngon are faces with more than 4 sides.

    To debug the problem on the meshes you can use Maya's modeling
    tool: "Mesh > Cleanup..."

    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Mesh ngons"
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type='mesh', long=True)

        # Get all faces
        faces = ['{0}.f[*]'.format(node) for node in meshes]

        # Filter to n-sided polygon faces (ngons)
        invalid = lib.polyConstraint(faces,
                                     t=0x0008,  # type=face
                                     size=3)    # size=nsided

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance "objectSet"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Meshes found with n-gons"
                             "values: {0}".format(invalid))
