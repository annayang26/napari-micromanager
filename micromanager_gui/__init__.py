try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from napari_plugin_engine import napari_hook_implementation


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    from .main_window import MainWindow

    return MainWindow


@napari_hook_implementation
def napari_experimental_provide_function():
    from _plugins import add_lut, hide_show

    return [add_lut, hide_show]
