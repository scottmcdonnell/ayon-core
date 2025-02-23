"""Core pipeline functionality"""

import os
import types
import logging
import platform
import uuid

import pyblish.api
from pyblish.lib import MessageHandler

from ayon_core import AYON_CORE_ROOT
from ayon_core.host import HostBase
from ayon_core.client import (
    get_project,
    get_asset_by_id,
    get_asset_by_name,
    version_is_latest,
    get_asset_name_identifier,
    get_ayon_server_api_connection,
)
from ayon_core.lib import is_in_tests
from ayon_core.lib.events import emit_event
from ayon_core.addon import load_addons, AddonsManager
from ayon_core.settings import get_project_settings

from .publish.lib import filter_pyblish_plugins
from .anatomy import Anatomy
from .template_data import get_template_data_with_names
from .workfile import (
    get_workdir,
    get_workfile_template_key,
    get_custom_workfile_template_by_string_context,
)
from . import (
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_inventory_action_path
)


_is_installed = False
_process_id = None
_registered_root = {"_": {}}
_registered_host = {"_": None}
# Keep modules manager (and it's modules) in memory
# - that gives option to register modules' callbacks
_addons_manager = None

log = logging.getLogger(__name__)

PLUGINS_DIR = os.path.join(AYON_CORE_ROOT, "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def _get_addons_manager():
    """Get or create modules manager for host installation.

    This is not meant for public usage. Reason is to keep modules
    in memory of process to be able trigger their event callbacks if they
    need any.

    Returns:
        AddonsManager: Manager wrapping discovered modules.
    """

    global _addons_manager
    if _addons_manager is None:
        _addons_manager = AddonsManager()
    return _addons_manager


def register_root(path):
    """Register currently active root"""
    log.info("Registering root: %s" % path)
    _registered_root["_"] = path


def registered_root():
    """Return registered roots from current project anatomy.

    Consider this does return roots only for current project and current
        platforms, only if host was installer using 'install_host'.

    Deprecated:
        Please use project 'Anatomy' to get roots. This function is still used
            at current core functions of load logic, but that will change
            in future and this function will be removed eventually. Using this
            function at new places can cause problems in the future.

    Returns:
        dict[str, str]: Root paths.
    """

    return _registered_root["_"]


def install_host(host):
    """Install `host` into the running Python session.

    Args:
        host (module): A Python module containing the Avalon
            avalon host-interface.
    """
    global _is_installed

    _is_installed = True

    # Make sure global AYON connection has set site id and version
    get_ayon_server_api_connection()

    addons_manager = _get_addons_manager()

    project_name = os.getenv("AYON_PROJECT_NAME")
    # WARNING: This might be an issue
    #   - commented out because 'traypublisher' does not have set project
    # if not project_name:
    #     raise ValueError(
    #         "AYON_PROJECT_NAME is missing in environment variables."
    #     )

    log.info("Activating {}..".format(project_name))

    # Optional host install function
    if hasattr(host, "install"):
        host.install()

    register_host(host)

    def modified_emit(obj, record):
        """Method replacing `emit` in Pyblish's MessageHandler."""
        record.msg = record.getMessage()
        obj.records.append(record)

    MessageHandler.emit = modified_emit

    if os.environ.get("AYON_REMOTE_PUBLISH"):
        # target "farm" == rendering on farm, expects AYON_PUBLISH_DATA
        # target "remote" == remote execution, installs host
        print("Registering pyblish target: remote")
        pyblish.api.register_target("remote")
    else:
        pyblish.api.register_target("local")

    if is_in_tests():
        print("Registering pyblish target: automated")
        pyblish.api.register_target("automated")

    host_name = os.environ.get("AYON_HOST_NAME")

    # Give option to handle host installation
    for addon in addons_manager.get_enabled_addons():
        addon.on_host_install(host, host_name, project_name)

    install_ayon_plugins(project_name, host_name)


def install_ayon_plugins(project_name=None, host_name=None):
    # Make sure modules are loaded
    load_addons()

    log.info("Registering global plug-ins..")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    pyblish.api.register_discovery_filter(filter_pyblish_plugins)
    register_loader_plugin_path(LOAD_PATH)
    register_inventory_action_path(INVENTORY_PATH)

    if host_name is None:
        host_name = os.environ.get("AYON_HOST_NAME")

    addons_manager = _get_addons_manager()
    publish_plugin_dirs = addons_manager.collect_publish_plugin_paths(
        host_name)
    for path in publish_plugin_dirs:
        pyblish.api.register_plugin_path(path)

    create_plugin_paths = addons_manager.collect_create_plugin_paths(
        host_name)
    for path in create_plugin_paths:
        register_creator_plugin_path(path)

    load_plugin_paths = addons_manager.collect_load_plugin_paths(
        host_name)
    for path in load_plugin_paths:
        register_loader_plugin_path(path)

    inventory_action_paths = addons_manager.collect_inventory_action_paths(
        host_name)
    for path in inventory_action_paths:
        register_inventory_action_path(path)

    if project_name is None:
        project_name = os.environ.get("AYON_PROJECT_NAME")

    # Register studio specific plugins
    if project_name:
        anatomy = Anatomy(project_name)
        anatomy.set_root_environments()
        register_root(anatomy.roots)

        project_settings = get_project_settings(project_name)
        platform_name = platform.system().lower()
        project_plugins = (
            project_settings
            ["core"]
            ["project_plugins"]
            .get(platform_name)
        ) or []
        for path in project_plugins:
            try:
                path = str(path.format(**os.environ))
            except KeyError:
                pass

            if not path or not os.path.exists(path):
                continue

            pyblish.api.register_plugin_path(path)
            register_loader_plugin_path(path)
            register_creator_plugin_path(path)
            register_inventory_action_path(path)


def install_openpype_plugins(project_name=None, host_name=None):
    install_ayon_plugins(project_name, host_name)


def uninstall_host():
    """Undo all of what `install()` did"""
    host = registered_host()

    try:
        host.uninstall()
    except AttributeError:
        pass

    log.info("Deregistering global plug-ins..")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    pyblish.api.deregister_discovery_filter(filter_pyblish_plugins)
    deregister_loader_plugin_path(LOAD_PATH)
    deregister_inventory_action_path(INVENTORY_PATH)
    log.info("Global plug-ins unregistred")

    deregister_host()

    log.info("Successfully uninstalled Avalon!")


def is_installed():
    """Return state of installation

    Returns:
        True if installed, False otherwise

    """

    return _is_installed


def register_host(host):
    """Register a new host for the current process

    Arguments:
        host (ModuleType): A module implementing the
            Host API interface. See the Host API
            documentation for details on what is
            required, or browse the source code.

    """

    _registered_host["_"] = host


def registered_host():
    """Return currently registered host"""
    return _registered_host["_"]


def deregister_host():
    _registered_host["_"] = None


def debug_host():
    """A debug host, useful to debugging features that depend on a host"""

    host = types.ModuleType("debugHost")

    def ls():
        containers = [
            {
                "representation": "ee-ft-a-uuid1",
                "schema": "openpype:container-1.0",
                "name": "Bruce01",
                "objectName": "Bruce01_node",
                "namespace": "_bruce01_",
                "version": 3,
            },
            {
                "representation": "aa-bc-s-uuid2",
                "schema": "openpype:container-1.0",
                "name": "Bruce02",
                "objectName": "Bruce01_node",
                "namespace": "_bruce02_",
                "version": 2,
            }
        ]

        for container in containers:
            yield container

    host.__dict__.update({
        "ls": ls,
        "open_file": lambda fname: None,
        "save_file": lambda fname: None,
        "current_file": lambda: os.path.expanduser("~/temp.txt"),
        "has_unsaved_changes": lambda: False,
        "work_root": lambda: os.path.expanduser("~/temp"),
        "file_extensions": lambda: ["txt"],
    })

    return host


def get_current_host_name():
    """Current host name.

    Function is based on currently registered host integration or environment
    variable 'AYON_HOST_NAME'.

    Returns:
        Union[str, None]: Name of host integration in current process or None.
    """

    host = registered_host()
    if isinstance(host, HostBase):
        return host.name
    return os.environ.get("AYON_HOST_NAME")


def get_global_context():
    """Global context defined in environment variables.

    Values here may not reflect current context of host integration. The
    function can be used on startup before a host is registered.

    Use 'get_current_context' to make sure you'll get current host integration
    context info.

    Example:
        {
            "project_name": "Commercial",
            "folder_path": "Bunny",
            "task_name": "Animation",
        }

    Returns:
        dict[str, Union[str, None]]: Context defined with environment
            variables.
    """

    return {
        "project_name": os.environ.get("AYON_PROJECT_NAME"),
        "folder_path": os.environ.get("AYON_FOLDER_PATH"),
        "task_name": os.environ.get("AYON_TASK_NAME"),
    }


def get_current_context():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_context()
    return get_global_context()


def get_current_project_name():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_project_name()
    return get_global_context()["project_name"]


def get_current_asset_name():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_asset_name()
    return get_global_context()["folder_path"]


def get_current_task_name():
    host = registered_host()
    if isinstance(host, HostBase):
        return host.get_current_task_name()
    return get_global_context()["task_name"]


def get_current_project(fields=None):
    """Helper function to get project document based on global Session.

    This function should be called only in process where host is installed.

    Returns:
        dict: Project document.
        None: Project is not set.
    """

    project_name = get_current_project_name()
    return get_project(project_name, fields=fields)


def get_current_project_asset(asset_name=None, asset_id=None, fields=None):
    """Helper function to get asset document based on global Session.

    This function should be called only in process where host is installed.

    Asset is found out based on passed asset name or id (not both). Asset name
    is not used for filtering if asset id is passed. When both asset name and
    id are missing then asset name from current process is used.

    Args:
        asset_name (str): Name of asset used for filter.
        asset_id (Union[str, ObjectId]): Asset document id. If entered then
            is used as only filter.
        fields (Union[List[str], None]): Limit returned data of asset documents
            to specific keys.

    Returns:
        dict: Asset document.
        None: Asset is not set or not exist.
    """

    project_name = get_current_project_name()
    if asset_id:
        return get_asset_by_id(project_name, asset_id, fields=fields)

    if not asset_name:
        asset_name = get_current_asset_name()
        # Skip if is not set even on context
        if not asset_name:
            return None
    return get_asset_by_name(project_name, asset_name, fields=fields)


def is_representation_from_latest(representation):
    """Return whether the representation is from latest version

    Args:
        representation (dict): The representation document from the database.

    Returns:
        bool: Whether the representation is of latest version.
    """

    project_name = get_current_project_name()
    return version_is_latest(project_name, representation["parent"])


def get_template_data_from_session(session=None, settings=None):
    """Template data for template fill from session keys.

    Args:
        session (Union[Dict[str, str], None]): The Session to use. If not
            provided use the currently active global Session.
        settings (Optional[Dict[str, Any]]): Prepared studio or project
            settings.

    Returns:
        Dict[str, Any]: All available data from session.
    """

    if session is not None:
        project_name = session["AYON_PROJECT_NAME"]
        asset_name = session["AYON_FOLDER_PATH"]
        task_name = session["AYON_TASK_NAME"]
        host_name = session["AYON_HOST_NAME"]
    else:
        context = get_current_context()
        project_name = context["project_name"]
        asset_name = context["folder_path"]
        task_name = context["task_name"]
        host_name = get_current_host_name()

    return get_template_data_with_names(
        project_name, asset_name, task_name, host_name, settings
    )


def get_current_context_template_data(settings=None):
    """Prepare template data for current context.

    Args:
        settings (Optional[Dict[str, Any]]): Prepared studio or
            project settings.

    Returns:
        Dict[str, Any] Template data for current context.
    """

    context = get_current_context()
    project_name = context["project_name"]
    asset_name = context["folder_path"]
    task_name = context["task_name"]
    host_name = get_current_host_name()

    return get_template_data_with_names(
        project_name, asset_name, task_name, host_name, settings
    )


def get_workdir_from_session(session=None, template_key=None):
    """Template data for template fill from session keys.

    Args:
        session (Union[Dict[str, str], None]): The Session to use. If not
            provided use the currently active global Session.
        template_key (str): Prepared template key from which workdir is
            calculated.

    Returns:
        str: Workdir path.
    """

    if session is not None:
        project_name = session["AYON_PROJECT_NAME"]
        host_name = session["AYON_HOST_NAME"]
    else:
        project_name = get_current_project_name()
        host_name = get_current_host_name()
    template_data = get_template_data_from_session(session)

    if not template_key:
        task_type = template_data["task"]["type"]
        template_key = get_workfile_template_key(
            task_type,
            host_name,
            project_name=project_name
        )

    anatomy = Anatomy(project_name)
    template_obj = anatomy.templates_obj[template_key]["folder"]
    path = template_obj.format_strict(template_data)
    if path:
        path = os.path.normpath(path)
    return path


def get_custom_workfile_template_from_session(
    session=None, project_settings=None
):
    """Filter and fill workfile template profiles by current context.

    This function cab be used only inside host where context is set.

    Args:
        session (Optional[Dict[str, str]]): Session from which are taken
            data.
        project_settings(Optional[Dict[str, Any]]): Project settings.

    Returns:
        str: Path to template or None if none of profiles match current
            context. (Existence of formatted path is not validated.)
    """

    if session is not None:
        project_name = session["AYON_PROJECT_NAME"]
        asset_name = session["AYON_FOLDER_PATH"]
        task_name = session["AYON_TASK_NAME"]
        host_name = session["AYON_HOST_NAME"]
    else:
        context = get_current_context()
        project_name = context["project_name"]
        asset_name = context["folder_path"]
        task_name = context["task_name"]
        host_name = get_current_host_name()

    return get_custom_workfile_template_by_string_context(
        project_name,
        asset_name,
        task_name,
        host_name,
        project_settings=project_settings
    )


def change_current_context(asset_doc, task_name, template_key=None):
    """Update active Session to a new task work area.

    This updates the live Session to a different task under asset.

    Args:
        asset_doc (Dict[str, Any]): The asset document to set.
        task_name (str): The task to set under asset.
        template_key (Union[str, None]): Prepared template key to be used for
            workfile template in Anatomy.

    Returns:
        Dict[str, str]: The changed key, values in the current Session.
    """

    project_name = get_current_project_name()
    workdir = None
    if asset_doc:
        project_doc = get_project(project_name)
        host_name = get_current_host_name()
        workdir = get_workdir(
            project_doc,
            asset_doc,
            task_name,
            host_name,
            template_key=template_key
        )

    folder_path = get_asset_name_identifier(asset_doc)
    envs = {
        "AYON_PROJECT_NAME": project_name,
        "AYON_FOLDER_PATH": folder_path,
        "AYON_TASK_NAME": task_name,
        "AYON_WORKDIR": workdir,
    }

    # Update the Session and environments. Pop from environments all keys with
    # value set to None.
    for key, value in envs.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    data = envs.copy()

    # Convert env keys to human readable keys
    data["project_name"] = project_name
    data["folder_path"] = get_asset_name_identifier(asset_doc)
    data["task_name"] = task_name
    data["workdir_path"] = workdir

    # Emit session change
    emit_event("taskChanged", data)

    return data


def get_process_id():
    """Fake process id created on demand using uuid.

    Can be used to create process specific folders in temp directory.

    Returns:
        str: Process id.
    """

    global _process_id
    if _process_id is None:
        _process_id = str(uuid.uuid4())
    return _process_id
