#!/usr/bin/env python3
# See usage().

import sys;
import os;
script_dir=os.path.dirname(os.path.abspath(__file__));
sys.path.append(script_dir + "/compogit_py_lib");

import compogit_get_component_from_compospec;
import glob_to_regex;

operations = {
  "ann-components-to-filelist-given-compospec": compogit_get_component_from_compospec.main,
  "get-components-of-filelist-from-compospec": compogit_get_component_from_compospec.main_get_component_names,
  "filter-filelist-for-component-from-compospec": compogit_get_component_from_compospec.main_filter,
  "glob-to-regex": glob_to_regex.main
};


if __name__ == "__main__":
  op = sys.argv[1]; #:_
  del sys.argv[1];
  if (op in operations):
    operations[op]();
  else:
    raise ValueError("Unknown operation: " + op);
