# PyInstaller entry point for the console-capable background core.
# Running jarvis as a module preserves the source project's existing startup behavior.
import runpy

runpy.run_module("jarvis", run_name="__main__", alter_sys=True)
