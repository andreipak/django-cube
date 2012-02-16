from django.utils.unittest import TestCase

from django_cube.cube import Cube, Measure, Dimension


class SimpleCountMeasure(Measure):

    def compute(self, cube):
        return len(self.filter(cube))

    def filter(self, cube):
        filtered = []
        for item in cube.data:
            for k, v in cube._constraint.items():
                if not item[k] == v:
                    break
            else:
                filtered.append(item)
        return filtered


class SimpleDimension(Dimension):

    pass


class SimpleCube(Cube):

    def __init__(self, data):
        self.data = data
        super(SimpleCube, self).__init__(
            dimensions=[SimpleDimension(name='instrument'), SimpleDimension(name='first_name')],
            measures=[SimpleCountMeasure()]
        )

    def get_sample_space(self):
        return [
            {'first_name': 'Bill', 'instrument': 'piano'},
            {'first_name': 'Bill', 'instrument': 'sax'},
            {'first_name': 'Bill', 'instrument': 'trumpet'},
            {'first_name': 'Miles', 'instrument': 'piano'},
            {'first_name': 'Miles', 'instrument': 'sax'},
            {'first_name': 'Miles', 'instrument': 'trumpet'},
            {'first_name': 'Thelonious', 'instrument': 'piano'},
            {'first_name': 'Thelonious', 'instrument': 'sax'},
            {'first_name': 'Thelonious', 'instrument': 'trumpet'},
        ]


class CubeTest(TestCase):

    def compute_test(self):
        cube = SimpleCube(data=[
            {'first_name': 'Bill', 'last_name': 'Evans', 'instrument': 'piano'},
            {'first_name': 'Bill', 'last_name': 'Evans', 'instrument': 'saxophone'},
            {'first_name': 'Miles', 'last_name': 'Davis', 'instrument': 'trumpet'}
        ])

        self.assertEqual(cube.compute(), (3,))

        slc = cube.slice(first_name='Miles', instrument='trumpet')
        self.assertEqual(slc.compute(), (1,))
