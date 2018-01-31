import unittest
from mesh_bed_leveling import MeshBedLeveling


class MyTestCase(unittest.TestCase):

    def test_leveling_is_the_same_as_measurements(self):
        measurements = [0.5, 1.0, 0, 0]
        locations = [[0, 0], [275, 290], [275, 0], [0, 290]]

        leveling = MeshBedLeveling(bed_max_x=275, bed_max_y=290)
        leveling.setup_interpolation(locations, measurements)

        self.assertEqual(0.0, leveling.compensation_for_coordinate(275, 0))
        self.assertEqual(0.0, leveling.compensation_for_coordinate(0, 290))
        self.assertEqual(0.5, leveling.compensation_for_coordinate(0, 0))
        self.assertEqual(1.0, leveling.compensation_for_coordinate(275, 290))

    def test_interpolate_between_measure_points(self):
        measurements = [0, 0, 0, 0, 1]
        locations = [[0, 0], [0, 200], [200, 0], [200, 200], [100, 100]]

        leveling = MeshBedLeveling(bed_max_x=200, bed_max_y=200)
        leveling.setup_interpolation(locations, measurements)

        self.assertEquals(0.5, leveling.compensation_for_coordinate(50, 50))
        self.assertEquals(0.5, leveling.compensation_for_coordinate(50, 150))
        self.assertEquals(0.5, leveling.compensation_for_coordinate(150, 50))
        self.assertEquals(0.5, leveling.compensation_for_coordinate(150, 150))
        self.assertEquals(0.25, leveling.compensation_for_coordinate(25, 25))
        self.assertEquals(0.0, leveling.compensation_for_coordinate(0, 150))
        self.assertEquals(0.0, leveling.compensation_for_coordinate(150, 0))
        self.assertEquals(0.0, leveling.compensation_for_coordinate(200, 100))
        self.assertEquals(0.0, leveling.compensation_for_coordinate(100, 200))

    def test_returns_zero_outside_of_bed(self):
        measurements = [0, 0, 0, 0, 1]
        locations = [[0, 0], [0, 200], [200, 0], [200, 200], [100, 100]]

        leveling = MeshBedLeveling(bed_max_x=200, bed_max_y=200)
        leveling.setup_interpolation(locations, measurements)

        self.assertEquals(0, leveling.compensation_for_coordinate(250, 100))
        self.assertEquals(0, leveling.compensation_for_coordinate(50, 300))
        self.assertEquals(0, leveling.compensation_for_coordinate(350, 300))

    def test_returns_correct_compensation_for_double_coordinates(self):
        measurements = [0, 0, 0, 0, 1]
        locations = [[0, 0], [0, 200], [200, 0], [200, 200], [100, 100]]

        leveling = MeshBedLeveling(bed_max_x=200, bed_max_y=200)
        leveling.setup_interpolation(locations, measurements)

        self.assertEquals(0.5, leveling.compensation_for_coordinate(50.0, 50.0))
        self.assertEquals(leveling.compensation_for_coordinate(6, 6),
                          leveling.compensation_for_coordinate(6.25, 6.25))
        self.assertEquals(leveling.compensation_for_coordinate(7, 7),
                          leveling.compensation_for_coordinate(6.5, 6.5))
