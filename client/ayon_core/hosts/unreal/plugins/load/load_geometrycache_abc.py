# -*- coding: utf-8 -*-
"""Loader for published alembics."""
import os

from ayon_core.pipeline import (
    get_representation_path,
    AYON_CONTAINER_ID
)
from ayon_core.hosts.unreal.api import plugin
from ayon_core.hosts.unreal.api.pipeline import (
    AYON_ASSET_DIR,
    create_container,
    imprint,
)

import unreal  # noqa


class PointCacheAlembicLoader(plugin.Loader):
    """Load Point Cache from Alembic"""

    families = ["model", "pointcache"]
    label = "Import Alembic Point Cache"
    representations = ["abc"]
    icon = "cube"
    color = "orange"

    root = AYON_ASSET_DIR

    @staticmethod
    def get_task(
        filename, asset_dir, asset_name, replace,
        frame_start=None, frame_end=None
    ):
        task = unreal.AssetImportTask()
        options = unreal.AbcImportSettings()
        gc_settings = unreal.AbcGeometryCacheSettings()
        conversion_settings = unreal.AbcConversionSettings()
        sampling_settings = unreal.AbcSamplingSettings()

        task.set_editor_property('filename', filename)
        task.set_editor_property('destination_path', asset_dir)
        task.set_editor_property('destination_name', asset_name)
        task.set_editor_property('replace_existing', replace)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        options.set_editor_property(
            'import_type', unreal.AlembicImportType.GEOMETRY_CACHE)

        gc_settings.set_editor_property('flatten_tracks', False)

        conversion_settings.set_editor_property('flip_u', False)
        conversion_settings.set_editor_property('flip_v', True)
        conversion_settings.set_editor_property(
            'scale', unreal.Vector(x=100.0, y=100.0, z=100.0))
        conversion_settings.set_editor_property(
            'rotation', unreal.Vector(x=-90.0, y=0.0, z=180.0))

        if frame_start is not None:
            sampling_settings.set_editor_property('frame_start', frame_start)
        if frame_end is not None:
            sampling_settings.set_editor_property('frame_end', frame_end)

        options.geometry_cache_settings = gc_settings
        options.conversion_settings = conversion_settings
        options.sampling_settings = sampling_settings
        task.options = options

        return task

    def import_and_containerize(
        self, filepath, asset_dir, asset_name, container_name,
        frame_start, frame_end
    ):
        unreal.EditorAssetLibrary.make_directory(asset_dir)

        task = self.get_task(
            filepath, asset_dir, asset_name, False, frame_start, frame_end)

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        # Create Asset Container
        create_container(container=container_name, path=asset_dir)

    def imprint(
        self, asset, asset_dir, container_name, asset_name, representation,
        frame_start, frame_end
    ):
        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": representation["_id"],
            "parent": representation["parent"],
            "family": representation["context"]["family"],
            "frame_start": frame_start,
            "frame_end": frame_end
        }
        imprint(f"{asset_dir}/{container_name}", data)

    def load(self, context, name, namespace, options):
        """Load and containerise representation into Content Browser.

        Args:
            context (dict): application context
            name (str): Product name
            namespace (str): in Unreal this is basically path to container.
                             This is not passed here, so namespace is set
                             by `containerise()` because only then we know
                             real path.
            data (dict): Those would be data to be imprinted.

        Returns:
            list(str): list of container content
        """
        # Create directory for asset and Ayon container
        asset = context.get('asset').get('name')
        suffix = "_CON"
        asset_name = f"{asset}_{name}" if asset else f"{name}"
        version = context.get('version')
        # Check if version is hero version and use different name
        if not version.get("name") and version.get('type') == "hero_version":
            name_version = f"{name}_hero"
        else:
            name_version = f"{name}_v{version.get('name'):03d}"

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{self.root}/{asset}/{name_version}", suffix="")

        container_name += suffix

        frame_start = context.get('asset').get('data').get('frameStart')
        frame_end = context.get('asset').get('data').get('frameEnd')

        # If frame start and end are the same, we increase the end frame by
        # one, otherwise Unreal will not import it
        if frame_start == frame_end:
            frame_end += 1

        if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
            path = self.filepath_from_context(context)

            self.import_and_containerize(
                path, asset_dir, asset_name, container_name,
                frame_start, frame_end)

        self.imprint(
            asset, asset_dir, container_name, asset_name,
            context["representation"], frame_start, frame_end)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, context):
        asset_doc = context["asset"]
        subset_doc = context["subset"]
        version_doc = context["version"]
        repre_doc = context["representation"]

        # Create directory for asset and Ayon container
        folder_name = asset_doc["name"]
        product_name = subset_doc["name"]

        suffix = "_CON"
        asset_name = product_name
        if folder_name:
            asset_name = f"{folder_name}_{product_name}"

        # Check if version is hero version and use different name
        version = version_doc.get("name", -1)
        if version < 0:
            name_version = f"{product_name}_hero"
        else:
            name_version = f"{product_name}_v{version:03d}"
        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{self.root}/{folder_name}/{name_version}", suffix="")

        container_name += suffix

        frame_start = int(container.get("frame_start"))
        frame_end = int(container.get("frame_end"))

        if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
            path = get_representation_path(repre_doc)

            self.import_and_containerize(
                path, asset_dir, asset_name, container_name,
                frame_start, frame_end)

        self.imprint(
            folder_name, asset_dir, container_name, asset_name, repre_doc,
            frame_start, frame_end)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=False
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

    def remove(self, container):
        path = container["namespace"]
        parent_path = os.path.dirname(path)

        unreal.EditorAssetLibrary.delete_directory(path)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            parent_path, recursive=False
        )

        if len(asset_content) == 0:
            unreal.EditorAssetLibrary.delete_directory(parent_path)
