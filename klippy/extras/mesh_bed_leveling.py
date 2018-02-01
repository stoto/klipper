import numpy as np
from scipy.interpolate import griddata


class MeshBedLeveling:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.x_bed_size = config.getFloat('x_bed_size', 100.)
        self.y_bed_size = config.getFloat('y_bed_size', 100.)
        self.interpolator = Interpolator(self.x_bed_size, self.y_bed_size)
        self.interpolator.setup_interpolation([[0, 0], [self.x_bed_size, 0], [0, self.y_bed_size],
                                               [self.x_bed_size, self.y_bed_size]], [0, 0, 0, 0])

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
    def __init__(self, x_bed_size, y_bed_size):
        self.x_bed_size = x_bed_size
        self.y_bed_size = y_bed_size
        self.grid = None

    def setup_interpolation(self, measurement_coordinates, measurement_zheights):
        mesh_x = np.linspace(0, self.x_bed_size, self.x_bed_size + 1)
        mesh_y = np.linspace(0, self.y_bed_size, self.y_bed_size + 1)
        mesh_x, mesh_y = np.meshgrid(mesh_x, mesh_y)
        self.grid = griddata(np.array(measurement_coordinates), measurement_zheights, (mesh_x, mesh_y), method='linear')

    def compensation_for_coordinate(self, x, y):
        return self.grid.T[int(round(x))][int(round(y))] if self.is_inside_bed(x, y) else 0

    def is_inside_bed(self, x, y):
        return x <= self.x_bed_size and y <= self.y_bed_size


def load_config(config):
    if config.get_name() != 'mesh_bed_leveling':
        raise config.error("Invalid mesh_bed_leveling config name")
    return MeshBedLeveling(config)
