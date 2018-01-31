import numpy as np
from scipy.interpolate import griddata


class MeshBedLeveling:

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
