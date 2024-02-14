# -*- coding: utf-8 -*-
"""Creator plugin to create Redshift ROP."""
import hou  # noqa

from ayon_core.hosts.houdini.api import plugin
from ayon_core.lib import EnumDef, BoolDef


class CreateRedshiftROP(plugin.HoudiniCreator):
    """Redshift ROP"""

    identifier = "io.openpype.creators.houdini.redshift_rop"
    label = "Redshift ROP"
    family = "redshift_rop"
    icon = "magic"
    ext = "exr"
    multi_layered_mode = "No Multi-Layered EXR File"

    # Default to split export and render jobs
    split_render = True

    def create(self, subset_name, instance_data, pre_create_data):

        instance_data.pop("active", None)
        instance_data.update({"node_type": "Redshift_ROP"})
        # Add chunk size attribute
        instance_data["chunkSize"] = 10
        # Submit for job publishing
        instance_data["farm"] = pre_create_data.get("farm")

        instance = super(CreateRedshiftROP, self).create(
            subset_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        basename = instance_node.name()

        # Also create the linked Redshift IPR Rop
        try:
            ipr_rop = instance_node.parent().createNode(
                "Redshift_IPR", node_name=f"{basename}_IPR"
            )
        except hou.OperationFailed as e:
            raise plugin.OpenPypeCreatorError(
                (
                    "Cannot create Redshift node. Is Redshift "
                    "installed and enabled?"
                )
            ) from e

        # Move it to directly under the Redshift ROP
        ipr_rop.setPosition(instance_node.position() + hou.Vector2(0, -1))

        # Set the linked rop to the Redshift ROP
        ipr_rop.parm("linked_rop").set(instance_node.path())
        ext = pre_create_data.get("image_format")
        multi_layered_mode = pre_create_data.get("multi_layered_mode")

        ext_format_index = {"exr": 0, "tif": 1, "jpg": 2, "png": 3}
        multilayer_mode_index = {"No Multi-Layered EXR File": "1",
                                 "Full Multi-Layered EXR File": "2" }

        if multilayer_mode_index[multi_layered_mode] == "1": 
            filepath = "{renders_dir}{subset_name}/{subset_name}.{fmt}".format(
                renders_dir=hou.text.expandString("$HIP/pyblish/renders/"),
                subset_name=subset_name,
                fmt="${aov}.$F4.{ext}".format(aov="AOV", ext=ext)
            )
            multipart = False

        elif multilayer_mode_index[multi_layered_mode] == "2":
            filepath = "{renders_dir}{subset_name}/{subset_name}.$F4.{ext}".format(
                renders_dir=hou.text.expandString("$HIP/pyblish/renders/"),
                subset_name=subset_name,
                ext=ext
            )
            multipart = True

        parms = {
            # Render frame range
            "trange": 1,
            # Redshift ROP settings
            "RS_outputFileNamePrefix": filepath,
            "RS_outputMultilayerMode": multilayer_mode_index[multi_layered_mode],
            "RS_aovMultipart" : multipart,
            "RS_outputBeautyAOVSuffix": "beauty",
            "RS_outputFileFormat": ext_format_index[ext],
        }

        if self.selected_nodes:
            # set up the render camera from the selected node
            camera = None
            for node in self.selected_nodes:
                if node.type().name() == "cam":
                    camera = node.path()
            parms["RS_renderCamera"] = camera or ""

        export_dir = hou.text.expandString("$HIP/pyblish/rs/")
        rs_filepath = f"{export_dir}{subset_name}/{subset_name}.$F4.rs"
        parms["RS_archive_file"] = rs_filepath

        if pre_create_data.get("split_render", self.split_render):
            parms["RS_archive_enable"] = 1

        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    def remove_instances(self, instances):
        for instance in instances:
            node = instance.data.get("instance_node")

            ipr_node = hou.node(f"{node}_IPR")
            if ipr_node:
                ipr_node.destroy()

        return super(CreateRedshiftROP, self).remove_instances(instances)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateRedshiftROP, self).get_pre_create_attr_defs()
        image_format_enum = [
            "exr", "tif", "jpg", "png",
        ]
        multi_layered_mode = [
            "No Multi-Layered EXR File",
            "Full Multi-Layered EXR File"
        ]


        return attrs + [
            BoolDef("farm",
                    label="Submitting to Farm",
                    default=True),
            BoolDef("split_render",
                    label="Split export and render jobs",
                    default=self.split_render),
            EnumDef("image_format",
                    image_format_enum,
                    default=self.ext,
                    label="Image Format Options"),
            EnumDef("multi_layered_mode",
                    multi_layered_mode,
                    default=self.multi_layered_mode,
                    label="Multi-Layered EXR")
        ]
