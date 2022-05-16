import yaml

y_file = "micromanager_gui/_gui_objects/_hcs_widget/_well_plate.yaml"


def print_yaml(file: yaml, plate_name: str):
    print(
        file[plate_name].get("id"),
        "\n",
        f'circular: {file[plate_name].get("circular")}\n',
        f'rows: {file[plate_name].get("rows")}\n',
        f'cols: {file[plate_name].get("cols")}\n',
        f'well_spacing_x: {file[plate_name].get("well_spacing_x")} mm\n',
        f'well_spacing_y: {file[plate_name].get("well_spacing_y")} mm\n',
        f'well_size_x: {file[plate_name].get("well_size_x")} mm\n',
        f'well_size_y: {file[plate_name].get("well_size_y")} mm',
    )


with open(y_file) as file:
    wp = yaml.safe_load(file)

    for x in wp:
        print("_________")
        print_yaml(wp, x)
    print("_________")
