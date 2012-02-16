import copy

from .utils import odict


class Measure(object):

    def compute(self, cube):
        raise NotImplementedError('This class is virtual')
        

class Dimension(object):
    """
    The base class for a dimension of a cube.

    Kwargs:
        sample_space (iterable|callable): The sample space of the dimension to create.
    """

    def __init__(self, sample_space=[], name=''):
        self._name = name
        self.sample_space = sample_space

    @property
    def name(self):
        """
        Returns:
            str. The name of the dimension.
        """
        return self._name

    @property
    def pretty_constraint(self, constraint):
        """
        Returns:
            str. A pretty string representation of **constraint**. 
        """
        return constraint

    def get_sample_space(self, sort=False):
        """
        Kwargs:
            sort(bool): whether to sort or not the sample space returned

        Returns:
            list. The sample space for the calling dimension.
        """
        raise NotImplementedError('This class is virtual')

    def _sort_sample_space(self, sample_space):
        """
        Args:
            sample_space (iterable). The sample space to sort, can be any iterable.

        Returns:
            list. The sample space sorted.
        """
        return sorted(list(sample_space))


class Cube(object):

    def __init__(self, measures, dimensions):
        self.measures = measures
        self.dimensions = dimensions
        self._constraint = {}

    def slice(self, **extra_constraint):
        """
        Returns a copy of the calling cube, with the updated constraint.
        the calling cube's *constraint* with *extra_constraint*. Example :

            >>> cube = MyCube(queryset)
            >>> subcube = cube.slice(dimensionA=2)
            >>> cube ; subcube
            MyCube(dimensionA)
            MyCube(dimensionA=2)
        """
        self._check_constraint(extra_constraint)
        cube_copy = copy.deepcopy(self)
        for dim_name, value in extra_constraint.iteritems():
            cube_copy._constraint[dim_name] = value
        return cube_copy

    def iter_slices(self, *dim_names):
        """
        A sorted iterator on all the slices with dimensions in *dim_names* constrained. It is sorted according to :meth:`sort_key`.

        .. note:: If one of the dimensions whose name passed as parameter is already constrained in the calling cube, it is not considered as an error.
        """
        self._check_dim_names(dim_names)
        dim_names = list(dim_names)
        free_dim_names = filter(self._is_constrained, dim_names)

        # if no free dimension, the cube is completely constrained,
        # no need to go further
        if not free_dim_names:
            yield copy.deepcopy(self)
            raise StopIteration

        #else, we get and sort the cube's sample space
        sample_space = self.get_sample_space(*free_dim_names)
        try:
            sample_space = sorted(sample_space, key=self.sort_key)
        except NotImplementedError:
            pass

        #and yield the slices
        for value in sample_space:
            yield self.slice(**value)
        raise StopIteration

    def compute(self):
        computed = []
        for measure in self.measures:
            computed.append(measure.compute(self))
        return tuple(computed)

    def get_sample_space(self, *dim_names):
        raise NotImplementedError('')

    @property
    def dim_names(self):
        return [d.name for d in self.dimensions]

    def _check_dim_names(self, dim_names):
        """
        Checks that `dim_names` are valid dimensions, or raises an error.
        """
        for dim_name in dim_names:
            if dim_name not in self.dim_names:
                raise ValueError('invalid dimension %s' % dim_name)

    def _check_constraint(self, constraint):
        """
        Checks that `constraint` is a valid constraint, or raises an error.
        """
        self._check_dim_names(constraint.keys())

    def _is_constrained(dim_name):
        """
        Returns True if `dim_name` is constrained, False otherwise.
        """
        return dim_name in self._constraint

    def _pop_first_dim(self, dim_names, free_only=False):
        """
        Pops the first dimension name from *dim_names*.

        Kwargs:
            free_only (bool): if True, only the dimensions that are not constrained will be poped.

        Returns:
            str|None. The poped dimension name, or None if there is no dimension name to pop.
        """
        for index, dim_name in enumerate(dim_names):
            if dim_name not in self.dimensions:
                raise ValueError("invalid dimension %s" % dim_name)
            #if dimension is constrained we don't need to iterate for it.
            if free_only and dim_name in self.constraint:
                continue
            else:
                return dim_names.pop(index)
        return None

    def __repr__(self):
        constr_dimensions = sorted(['%s=%s' % (dim, value) for dim, value in self._constraint.iteritems()])
        free_dimensions = sorted(list(set(self.dim_names) - set(self._constraint)))
        return 'Cube(%s)' % ', '.join(free_dimensions + constr_dimensions)

    def measures_dict(self, *dim_names, **kwargs):
        """
        """
        # prepare the iteration
        kwargs = kwargs.copy()
        self._check_dim_names(dim_names)
        full = kwargs.setdefault('full', True)
        returned_dict = odict()
        dim_names = list(dim_names)

        # if dim_names, we iter over all slices of the cube
        if dim_names:
            slices_dict = odict()
            for slc in self.iter_slices(next_dim_name):
                dim_value = slc.constraint[next_dim_name]
                slices_dict[dim_value] = slc.measures_dict(*dim_names, **kwargs)
            if full:
                returned_dict['measure'] = self.measure()
                returned_dict['slices'] = slices_dict
            else:
                returned_dict = slices_dict
        # else, we just need the measure on the whole cube
        else:
            returned_dict['measure'] = self.measure()
        return returned_dict

    def measures_list(self, *dim_names):
        """
        """
        returned_list = []

        dim_names = list(dim_names)
        next_dim_name = self._pop_first_dim(dim_names)
        
        # We check if there is still dimensions in *dim_names*,
        # otherwise we return a list of measures. 
        if dim_names:
            for slc in self.iter_slices(next_dim_name):
                returned_list.append(slc.measures_list(*dim_names))
        elif next_dim_name:
            for slc in self.iter_slices(next_dim_name):
                returned_list.append(slc.measure())
        return returned_list
    
    def measures(self, *dim_names):
        """
        Returns:
            list. A list of dictionnaries, whose keys are values for dimensions in *dim_names* and a special key *'__measure'*, for the measure associated with these dimensions' values. This is actually very similar to Django querysets' "values" method. For example :

                >>> cube.measures('dim2', 'dim1') == [
                ...     [{'dim1': val1_1, 'dim2': val2_1, '__measure': measure_1_1},
                ...     , ,
                ...     {'dim1': val1_N, 'dim2': val2_N, '__measure': measure_1_1}]
        """
        dim_names = list(dim_names)
        dict_list = []
        for subcube in self.subcubes(*dim_names):
            measure_dict = subcube.constraint
            measure_dict['__measure'] = subcube.measure()
            dict_list.append(measure_dict)
        return dict_list
