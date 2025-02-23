# -*- coding: utf-8 -*-
"""Validator for correct naming of Static Meshes."""
import pyblish.api
from ayon_core.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from ayon_core.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
)
from ayon_core.hosts.houdini.api.action import SelectInvalidAction
from ayon_core.pipeline.create import get_product_name

import hou


class FixSubsetNameAction(RepairAction):
    label = "Fix Subset Name"


class ValidateSubsetName(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validate Subset name.

    """

    families = ["staticMesh"]
    hosts = ["houdini"]
    label = "Validate Subset Name"
    order = ValidateContentsOrder + 0.1
    actions = [FixSubsetNameAction, SelectInvalidAction]

    optional = True

    def process(self, instance):

        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.path() for n in invalid]
            raise PublishValidationError(
                "See log for details. "
                "Invalid nodes: {0}".format(nodes)
            )

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        rop_node = hou.node(instance.data["instance_node"])

        # Check product name
        asset_doc = instance.data["assetEntity"]
        product_name = get_product_name(
            instance.context.data["projectName"],
            asset_doc,
            instance.data["task"],
            instance.context.data["hostName"],
            instance.data["productType"],
            variant=instance.data["variant"],
            dynamic_data={"asset": asset_doc["name"]}
        )

        if instance.data.get("productName") != product_name:
            invalid.append(rop_node)
            cls.log.error(
                "Invalid product name on rop node '%s' should be '%s'.",
                rop_node.path(), product_name
            )

        return invalid

    @classmethod
    def repair(cls, instance):
        rop_node = hou.node(instance.data["instance_node"])

        # Check product name
        asset_doc = instance.data["assetEntity"]
        product_name = get_product_name(
            instance.context.data["projectName"],
            asset_doc,
            instance.data["task"],
            instance.context.data["hostName"],
            instance.data["productType"],
            variant=instance.data["variant"],
            dynamic_data={"asset": asset_doc["name"]}
        )

        instance.data["productName"] = product_name
        rop_node.parm("AYON_productName").set(product_name)

        cls.log.debug(
            "Product name on rop node '%s' has been set to '%s'.",
            rop_node.path(), product_name
        )
