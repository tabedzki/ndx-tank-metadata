import os
from shutil import copy2

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):  # Note the class name change
    def initialize(self, version, build_data):
        """Run before the build process begins"""
        project_dir = os.path.dirname(__file__)
        ns_path = os.path.join(project_dir, "spec", "ndx-tank-metadata.namespace.yaml")
        ext_path = os.path.join(
            project_dir, "spec", "ndx-tank-metadata.extensions.yaml"
        )

        dst_dir = os.path.join(project_dir, "src", "pynwb", "ndx_tank_metadata", "spec")
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)

        copy2(ns_path, dst_dir)
        copy2(ext_path, dst_dir)
