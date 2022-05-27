from useq import MDAEvent, MDASequence, Position


def event_indices(event: MDAEvent):
    for k in event.sequence.axis_order if event.sequence else []:
        if k in event.index:
            yield k


def _interpret_split_position(sequence: MDASequence):
    """
    Determine the shape of layers and the dimension labels based
    on whether we are splitting on channels
    """
    _meta_split_positions = True
    img_shape = 512, 512
    # dimensions labels
    axis_order = event_indices(next(sequence.iter_events()))
    labels = []
    shape = []
    for i, a in enumerate(axis_order):
        dim = sequence.shape[i]
        if dim != 1:
            labels.append(a)
            shape.append(dim)
    labels.extend(["y", "x"])
    shape.extend(img_shape)

    if _meta_split_positions:

        positions = []
        sub_positions = []

        for p in sequence.stage_positions:
            well = p.name.split("_")[0]
            pos = p.name.split("_")[-1]
            if f"{well}_" not in positions:
                positions.append(f"{well}_")
            if pos not in sub_positions:
                sub_positions.append(pos)

        p_idx = labels.index("p")
        new_p_shape = int(shape[p_idx] / len(sub_positions))
        if new_p_shape > 1:
            shape[p_idx] = new_p_shape
        else:
            shape.pop(p_idx)

    return shape, positions, sub_positions, labels


def _add_hcs_position_layers(shape, positions, sub_positions, sequence: MDASequence):

    # create a zarr store for each channel (or all channels when not splitting)
    # to store the images to display so we don't overflow memory.
    for position in positions:
        id_ = position + str(sequence.uid)
        print("id_:", id_)


a = Position(x=100, y=1, z=1, name="A1_pos000")
b = Position(x=200, y=1, z=1, name="A1_pos001")
c = Position(x=100, y=1, z=1, name="B1_pos000")
d = Position(x=200, y=1, z=1, name="B1_pos001")

sequence = MDASequence(
    channels=[{"config": "FITC", "exposure": 50}],
    axis_order="tpcz",
    stage_positions=[a, b, c, d],
)


for e in list(sequence.iter_events()):
    print(e)
    print()


# shape, positions, sub_positions, labels = _interpret_split_position(sequence)
# print(shape, positions, sub_positions, labels)

# _add_hcs_position_layers(shape, positions, sub_positions, sequence)
