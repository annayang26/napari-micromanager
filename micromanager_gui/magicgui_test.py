from magicgui import magicgui
from magicgui.widgets import Container
from pymmcore_plus import RemoteMMCore

mmc = RemoteMMCore()
mmc.loadSystemConfiguration("micromanager_gui/s15_Nikon_Ti1.cfg")

light_list = ["dia", "epi", "lumencor"]

c = Container(labels=False)
for cfg in mmc.getAvailableConfigGroups():
    cfg_lower = cfg.lower()
    if cfg_lower in light_list:
        cfg_groups_options = mmc.getAvailableConfigs(cfg)
        cfg_groups_options_keys = (mmc.getConfigData(cfg, cfg_groups_options[0])).dict()

        dev_name = [
            k for idx, k in enumerate(cfg_groups_options_keys.keys()) if idx == 0
        ][0]

        for prop in mmc.getDevicePropertyNames(dev_name):
            has_range = mmc.hasPropertyLimits(dev_name, prop)
            lower_lim = mmc.getPropertyLowerLimit(dev_name, prop)
            upper_lim = mmc.getPropertyUpperLimit(dev_name, prop)

            if has_range and "intensity" in str(prop).lower():
                # print(dev_name, prop, has_range, lower_lim, upper_lim)

                @magicgui(
                    auto_call=True,
                    layout="vertical",
                    dev_name={"bind": dev_name},
                    prop={"bind": prop},
                    slider_float={
                        "label": f"{dev_name}_{prop}",
                        "widget_type": "FloatSlider",
                        "max": upper_lim,
                        "min": lower_lim,
                    },
                )
                def sl(dev_name, prop, slider_float=10):
                    mmc.setProperty(dev_name, prop, slider_float)
                    print(prop, mmc.getProperty(dev_name, prop))

                c.append(sl)

c.show(run=True)


# c = Container(labels=False)

# for dev in mmc.getLoadedDevices():
#     dev_type = DeviceType(mmc.getDeviceType(dev))
#     for prop in mmc.getDevicePropertyNames(dev):
#         has_range = mmc.hasPropertyLimits(dev, prop)
#         lower_lim = mmc.getPropertyLowerLimit(dev, prop)
#         upper_lim = mmc.getPropertyUpperLimit(dev, prop)
#         if has_range:
#             print(dev, dev_type, prop, has_range, lower_lim, upper_lim)

#             @magicgui(
#                 auto_call=True,
#                 layout="vertical",
#                 slider_float={
#                     "label": f"{dev}_{prop}",
#                     "widget_type": "FloatSlider",
#                     "max": upper_lim,
#                     "min": lower_lim,
#                 },
#             )
#             def sl(slider_float):
#                 print(slider_float)

#             c.append(sl)

# c.show(run=True)
