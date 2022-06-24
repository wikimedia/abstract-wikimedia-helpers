import contextlib
import io
import json
import os
import re
import sys
import yaml


_Z9_REGEX = re.compile(r'^(Z([1-9]\d*K)?)|K[1-9]\d*$')


def _is_Z10(normal_zobject):
    Z1K1 = normal_zobject.get('Z1K1', {})
    if not isinstance(Z1K1, dict):
        return False
    return Z1K1.get('Z9K1') == 'Z10'


def _is_Z9(normal_zobject):
    return normal_zobject.get('Z1K1') == 'Z9' and normal_zobject.get('Z9K1') is not None


def _is_Z6(normal_zobject):
    return normal_zobject.get('Z1K1') == 'Z6' and normal_zobject.get('Z6K1') is not None


def _is_Z13(normal_zobject):
    return normal_zobject.get('Z1K1') == 'Z13'


def _Z10_to_array(normal_zobject):
    root = normal_zobject
    result = []
    while True:
        element = root.get('Z10K1')
        if element is None:
            break
        result.append(element)
        root = root.get('Z10K2', {})
    return result


def _canonicalize(zobject):
    if not isinstance(zobject, dict):
        return zobject
    if _is_Z13(zobject):
        return zobject
    if _is_Z9(zobject):
        return zobject['Z9K1']
    if _is_Z6(zobject):
        try:
            if _Z9_REGEX.search(zobject['Z6K1']):
                return zobject
        except:
            pass
        return zobject['Z6K1']
    if _is_Z10(zobject):
        return list(map(_canonicalize, _Z10_to_array(zobject)))
    result = {}
    for key, value in zobject.items():
        result[key] = _canonicalize(value)
    return result


def _Z9( ZID ):
    return { 'Z1K1': 'Z9', 'Z9K1': ZID }


@contextlib.contextmanager
def get_stringio():
    outp = io.StringIO()
    yield outp


@contextlib.contextmanager
def printable_stringio():
    with get_stringio() as outp:
        yield outp
        outp.seek(0)
        print(outp.read())


class Helper:

    def __init__(self, fname, dry_run=True, mode='yaml'):
        self._fname = fname
        self._dry_run = dry_run
        if mode == 'yaml':
            self._serializer = yaml
        else:
            self._serializer = json

    @property
    def _dump(self):
        if self._serializer is yaml:
            return yaml.dump
        else:
            return lambda x, outp: json.dump(x, outp, indent=4, separators=(',', ': '))

    @contextlib.contextmanager
    def _test_dict_and_outp(self):
        with open(self._fname, 'r') as inp:
            test_dict = self._serializer.load(inp)
        with open(self._fname, 'r') as inp:
            try:
                comment = next(inp).strip()
            except:
                comment = None
            else:
                if not re.search(r'^#', comment):
                    comment = None
        with get_stringio() as outp:
            yield test_dict, outp
            outp.seek(0)
            contents = outp.read()
        with contextlib.ExitStack() as stack:
            if self._dry_run:
                outp = stack.enter_context(printable_stringio())
            else:
                outp = stack.enter_context(open(self._fname, 'w'))
            if comment is not None:
                outp.write(f'{comment}\n')
            outp.write(contents)

    def add_tests(self):
        with self._test_dict_and_outp() as test_dict, outp:
            success = test_dict['test_objects']['success']
            success.append({
                'name': 'can be a Z9',
                'object': {
                    'Z1K1': 'Z9',
                    'Z9K1': 'Z1000'
                }
            })
            success.append({
                'name': 'can be a Z18',
                'object': {
                    'Z1K1': {
                        'Z1K1': 'Z9',
                        'Z9K1': 'Z18'
                    },
                    'Z18K1': {
                        'Z1K1': 'Z6',
                        'Z6K1': 'Z1000K1'
                    }
                }
            })
            self._dump(test_dict, outp)

    def canonicalize_Z1K1(self):
        ZID = re.search(r'.*\/(Z\d*.*?)\.yaml', self._fname).groups()[0]
        with self._test_dict_and_outp() as (test_dict, outp):
            literal = test_dict['definitions']['objects'][ZID + '_literal']
            literal['properties']['Z1K1'] = {
                'allOf': [
                    { '$ref': 'Z9#/definitions/objects/Z9' },
                    {
                        'enum': [ ZID ],
                        'type': 'string'
                    }
                ]
            }
            self._dump(test_dict, outp)

    def canonicalize_test_file(self):
        with self._test_dict_and_outp() as (test_dict, outp):
            for key in ['failure', 'success']:
                the_l = test_dict['test_objects'].get(key, [])
                for the_d in the_l:
                    the_d['object'] = _canonicalize(the_d['object'])
            self._dump(test_dict, outp)

    def _is_z10_type(self, Z1K1):
        if isinstance(Z1K1, dict):
            return Z1K1.get('Z1K1') == 'Z9' and Z1K1.get('Z9K1') == 'Z10'
        return Z1K1 == 'Z10'

    def _is_z7(self, Z1K1):
        if isinstance(Z1K1, dict):
            return Z1K1.get('Z1K1') == 'Z9' and Z1K1.get('Z9K1') == 'Z7'
        return Z1K1 == 'Z7'

    def _is_z881(self, Z1K1):
        if isinstance(Z1K1, dict):
            return Z1K1.get('Z1K1') == 'Z9' and Z1K1.get('Z9K1') == 'Z881'
        return Z1K1 == 'Z881'

    def _is_list_type(self, Z1K1):
        if isinstance(Z1K1, dict):
            return (
                self._is_z7(Z1K1.get('Z1K1', {})) and
                self._is_z881(Z1K1.get('Z7K1', {})))
        return False

    def _replace_z10s_recursive(self, zobject):
        if not isinstance(zobject, dict):
            return zobject
        result = {}
        for key, value in zobject.items():
            value = self._replace_z10s_recursive(value)
            if key == 'Z1K1' and self._is_z10_type(value):
                result[key] = {
                    'Z1K1': 'Z7',
                    'Z7K1': 'Z881',
                    'Z881K1': 'Z1'
                }
            elif key == 'Z10K1':
                result['K1'] = value
            elif key == 'Z10K2':
                result['K2'] = value
            else:
                result[key] = value
        return result

    def _array_to_typed_list(self, the_list, the_type=None):
        if the_type is None:
            if the_list:
                the_type = the_list[0]['Z1K1']
            else:
                the_type = { 'Z1K1': 'Z9', 'Z9K1': 'Z1' }
        if isinstance(the_type, str):
            the_type = _Z9(the_type)
        list_type = {
            'Z1K1': _Z9('Z7'),
            'Z7K1': _Z9('Z881'),
            'Z881K1': the_type
        }
        result = {
            'Z1K1': list_type
        }
        if the_list:
            result['K1'] = the_list.pop(0)
            result['K2'] = self._array_to_typed_list(the_list, the_type)
        return result

    def _with_all_arrays_as_typed_lists(self, zobject, the_type=None):
        if isinstance(zobject, str) or zobject is None:
            result = zobject
        elif isinstance(zobject, list):
            result = self._array_to_typed_list([
                self._with_all_arrays_as_typed_lists(element)
                for element in zobject], the_type)
        else:
            result = {}
            for key, value in zobject.items():
                if key == 'Z12K1':
                    the_type = _Z9('Z11')
                elif key == 'Z8K3':
                    the_type = _Z9('Z20')
                elif key == 'Z8K1':
                    the_type = _Z9('Z17')
                elif key == 'Z8K4':
                    the_type = _Z9('Z14')
                elif key == 'Z5K2':
                    the_type = _Z9('Z5')
                result[key] = self._with_all_arrays_as_typed_lists(value, the_type)
        return result

    def _with_z10s_as_arrays(self, zobject):
        if isinstance(zobject, list):
            return [self._with_z10s_as_arrays(element) for element in zobject]
        if isinstance(zobject, str):
            return zobject
        if zobject is None:
            return zobject
        if self._is_z10_type(zobject.get('Z1K1', {})):
            result = []
            element = zobject.get('Z10K1')
            if element is not None:
                result.append(self._with_z10s_as_arrays(element))
            tail = zobject.get('Z10K2')
            if tail is not None:
                result.extend(self._with_z10s_as_arrays(tail))
            return result
        result = {}
        for key, value in zobject.items():
            result[key] = self._with_z10s_as_arrays(value)
        return result

    def _with_all_lists_as_arrays(self, zobject):
        if isinstance(zobject, str) or zobject is None:
            result = zobject
        elif isinstance(zobject, list):
            result = [self._with_all_lists_as_arrays(element) for element in zobject]
        elif (
                self._is_z10_type(zobject.get('Z1K1', {})) or
                self._is_list_type(zobject.get('Z1K1', {}))):
            result = []
            element = zobject.get('Z10K1') or zobject.get('K1')
            if element is not None:
                result.append(self._with_all_lists_as_arrays(element))
            tail = zobject.get('Z10K2') or zobject.get('K2')
            if tail is not None:
                result.extend(self._with_all_lists_as_arrays(tail))
        else:
            result = {}
            for key, value in zobject.items():
                result[key] = self._with_all_lists_as_arrays(value)
        return result

    def replace_z10s(self):
        with self._test_dict_and_outp() as (test_dict, outp):
            self._dump(self._with_z10s_as_arrays(test_dict), outp)

    def remove_newline(self):
        with open(self._fname, 'r') as inp:
            contents = inp.read().rstrip('\n')
        if self._dry_run:
            print(contents)
        else:
            with open(self._fname, 'w') as outp:
                outp.write(contents)

    def _to_benjamin(self, array):
        the_type = 'Z1'
        if len(array) > 0:
            first_object = array[0]
            if isinstance(first_object, str):
                if _Z9_REGEX.search(first_object):
                    the_type = 'Z9'
                else:
                    the_type = 'Z6'
            else:
                the_type = first_object['Z1K1']
        array.insert(0, the_type)

    def _convert_arrays_to_benjamin(self, zobject):
        if isinstance(zobject, str):
            return
        elif isinstance(zobject, dict):
            for key, value in zobject.items():
                self._convert_arrays_to_benjamin(value)
        elif isinstance(zobject, list):
            self._to_benjamin(zobject)
            for sub_value in zobject:
                self._convert_arrays_to_benjamin(sub_value)

    def all_about_benjamins(self):
        with self._test_dict_and_outp() as (test_dict, outp):
            self._convert_arrays_to_benjamin(test_dict)
            self._dump(test_dict, outp)

    def canonicalize_with_z10s(self):
        with self._test_dict_and_outp() as (test_dict, outp):
            result = _canonicalize(test_dict)
            self._dump(result, outp)
    
    def replace_arrays_with_typed_lists(self):
        with self._test_dict_and_outp() as (test_dict, outp):
            result = self._with_all_lists_as_arrays(test_dict)
            result = self._with_all_arrays_as_typed_lists(result)
            self._dump(result, outp)
                

if __name__ == '__main__':
    import fire
    fire.Fire(Helper)
