import numpy as np
from scipy.interpolate import griddata


class MeshBedLeveling:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.bed_max_x = config.getFloat('bed_max_x', 100.)
        self.bed_max_y = config.getFloat('bed_max_y', 100.)
        self.interpolator = Interpolator(self.bed_max_x, self.bed_max_y)
        self.interpolator.setup_interpolation([[0, 0], [self.bed_max_x, 0], [0, self.bed_max_y],
                                               [self.bed_max_x, self.bed_max_y]], [0, 0, 0, 0])

        self.toolhead = None
        gcode = self.printer.lookup_object('gcode')
        gcode.set_move_transform(self)

    def printer_state(self, state):
        if state == 'connect':
            self.toolhead = self.printer.lookup_object('toolhead')

    def get_position(self):
        x, y, z, e = self.toolhead.get_position()
        return [x, y, z - self.interpolator.compensation_for_coordinate(x, y), e]

    def move(self, newpos, speed):
        x, y, z, e = newpos
        self.toolhead.move([x, y, z + self.interpolator.compensation_for_coordinate(x, y), e],
                           speed)


class Interpolator:
    def __init__(self, bed_max_x, bed_max_y):
        self.bed_max_x = bed_max_x
        self.bed_max_y = bed_max_y
        self.grid = None

    def setup_interpolation(self, measurement_coordinates, measurement_zheights):
        mesh_x = np.linspace(0, self.bed_max_x, self.bed_max_x + 1)
        mesh_y = np.linspace(0, self.bed_max_y, self.bed_max_y + 1)
        mesh_x, mesh_y = np.meshgrid(mesh_x, mesh_y)
        self.grid = griddata(np.array(measurement_coordinates), measurement_zheights, (mesh_x, mesh_y), method='linear')

    def compensation_for_coordinate(self, x, y):
        return self.grid.T[int(round(x))][int(round(y))] if self.is_inside_bed(x, y) else 0

    def is_inside_bed(self, x, y):
        return x <= self.bed_max_x and y <= self.bed_max_y


def load_config(config):
    if config.get_name() != 'mesh_bed_leveling':
        raise config.error("Invalid mesh_bed_leveling config name")
    return MeshBedLeveling(config)
