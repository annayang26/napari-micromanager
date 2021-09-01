import sys

from magicgui import magicgui
from magicgui.widgets import Container
from qtpy.QtWidgets import QApplication

group_name_list = ["dia_group_name", "epi_group_name", "objective_device_name"]


class InitialParameter(Container):
    def __init__(self):
        super().__init__()

    def make_magicgui(self):
        c = Container(labels=False)
        for g_name in group_name_list:

            @magicgui(
                layout="horizontal",
                call_button="save",
                group_name={"bind": g_name},
                wdg={
                    "label": f"{g_name}",
                    "widget_type": "LineEdit",
                },
            )
            def ln_wdg(wdg, group_name):
                print(f"{group_name}: {wdg}")

            c.append(ln_wdg)

        c.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    cls = InitialParameter()
    cls.make_magicgui()
    sys.exit(app.exec_())
