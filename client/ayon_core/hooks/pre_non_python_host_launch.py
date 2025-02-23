import os

from ayon_core.lib import get_ayon_launcher_args
from ayon_core.lib.applications import (
    get_non_python_host_kwargs,
    PreLaunchHook,
    LaunchTypes,
)

from ayon_core import AYON_CORE_ROOT


class NonPythonHostHook(PreLaunchHook):
    """Launch arguments preparation.

    Non python host implementation do not launch host directly but use
    python script which launch the host. For these cases it is necessary to
    prepend python (or ayon) executable and script path before application's.
    """
    app_groups = {"harmony", "photoshop", "aftereffects"}

    order = 20
    launch_types = {LaunchTypes.local}

    def execute(self):
        # Pop executable
        executable_path = self.launch_context.launch_args.pop(0)

        # Pop rest of launch arguments - There should not be other arguments!
        remainders = []
        while self.launch_context.launch_args:
            remainders.append(self.launch_context.launch_args.pop(0))

        script_path = os.path.join(
            AYON_CORE_ROOT,
            "scripts",
            "non_python_host_launch.py"
        )

        new_launch_args = get_ayon_launcher_args(
            "run", script_path, executable_path
        )
        # Add workfile path if exists
        workfile_path = self.data["last_workfile_path"]
        if (
                self.data.get("start_last_workfile")
                and workfile_path
                and os.path.exists(workfile_path)):
            new_launch_args.append(workfile_path)

        # Append as whole list as these areguments should not be separated
        self.launch_context.launch_args.append(new_launch_args)

        if remainders:
            self.launch_context.launch_args.extend(remainders)

        self.launch_context.kwargs = \
            get_non_python_host_kwargs(self.launch_context.kwargs)
