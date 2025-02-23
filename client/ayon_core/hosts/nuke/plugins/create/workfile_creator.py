import ayon_core.hosts.nuke.api as api
from ayon_core.client import get_asset_by_name
from ayon_core.pipeline import (
    AutoCreator,
    CreatedInstance,
)
from ayon_core.hosts.nuke.api import (
    INSTANCE_DATA_KNOB,
    set_node_data
)
import nuke


class WorkfileCreator(AutoCreator):
    identifier = "workfile"
    product_type = "workfile"

    default_variant = "Main"

    def get_instance_attr_defs(self):
        return []

    def collect_instances(self):
        root_node = nuke.root()
        instance_data = api.get_node_data(
            root_node, api.INSTANCE_DATA_KNOB
        )

        project_name = self.create_context.get_current_project_name()
        asset_name = self.create_context.get_current_asset_name()
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        asset_doc = get_asset_by_name(project_name, asset_name)
        product_name = self.get_product_name(
            project_name,
            asset_doc,
            task_name,
            self.default_variant,
            host_name,
        )
        instance_data.update({
            "asset": asset_name,
            "task": task_name,
            "variant": self.default_variant
        })
        instance_data.update(self.get_dynamic_data(
            project_name,
            asset_doc,
            task_name,
            self.default_variant,
            host_name,
            instance_data
        ))

        instance = CreatedInstance(
            self.product_type, product_name, instance_data, self
        )
        instance.transient_data["node"] = root_node
        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            instance_node = created_inst.transient_data["node"]

            set_node_data(
                instance_node,
                INSTANCE_DATA_KNOB,
                created_inst.data_to_store()
            )

    def create(self, options=None):
        # no need to create if it is created
        # in `collect_instances`
        pass
