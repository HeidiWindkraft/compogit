#!/usr/bin/env python3
# See usage().

import sys;
import re;
import json;
import fnmatch;

import glob_to_regex;


def usage():
  print (
"""
USAGE
  compogit-ann-components-to-filelist-given-compospec compospecjson < filelist

EXAMPLE
  find -type f | compogit-ann-components-to-filelist-given-compospec .compogit/compospec.json

DESCRIPTION
  Determines the component of the filepaths on STDIN and outputs them in the format "<COMPONENT_NAME>:<FILENAME>".
  The pathes must not use '..', which goes one directory up again.
  The pathes must be releative to the same path as the patterns in the compospec (component specification).
  The component specification is given in JSON format.
  Each compoenent can have the following fields:
    - path expressions:
      Path expressions describe the pathes at which files of the respective component reside.
      The different types of path expressions are merged to one list of patterns.
      The different types are:
        - 'path': A list of pathes.
        - 'fnmatch': A list of python fnmatch expressions.
        - 'glob': A list of glob patterns.
        - 'regex': A list of regular expressions.
    - 'overrides': The component which is overriden by this component (optional).
                   If the path expressions of multiple components match, then
                   a component A which overrides another component B
                   takes precedence over the other component B.
                   If both A and B match for a file, this file is in component A.
""",
    file=sys.stderr
  );


# Allowed component fields.
c_component_fields = {
  'overrides',
  'path',
  'fnmatch',
  'regex',
  'glob'
};

# A pattern to match component identifiers.
cr_compid = re.compile("^[_0-9a-zA-Z]+$");

def prepare_path(s):
  """ removes all redundant slashes from the given path
      and removes leading "./".
  """
  while ("//" in s):
    s = s.replace("//","/");
  if (s.startswith("./")):
    s = s[2:];
  return s;

def json_field_as_iterable(jsonobj, fieldname):
  """ returns the given json property field as list. """
  if (fieldname not in jsonobj):
    # Field doesn't exist -> empty list.
    return [];
  field = jsonobj[fieldname]; #:_
  if (isinstance(field,str)):
    # Field is a scalar -> wrap it in a list.
    return [ field ];
  else:
    # Field should be a list...
    return field;

class Component:
  """ This class represents components of a git repository. """
  __slots__ = (
    'name',           # The name of this component.
    'overrides',      # The component which is overriden by this one. TODO make it a list.
    'overrides_ref',  # Name of the component which is overriden by this one. TODO make it a list.
    'regexes'         # The regexes which match all files of this component.
  );
  def __init__(self, name):
    """ Set default values for this class' fields. """
    self.name = name;
    self.overrides = None;
    self.overrides_ref = "";
    self.regexes = [];
  def fromJson(self, jsonobj):
    """ Fill this object from a json object. """
    for key in jsonobj.keys():
      if (key not in c_component_fields):
        raise ValueError("UnknownComponentField: Unknown component field in '" + self.name + "': " + key);
    if ('overrides' in jsonobj):
      self.overrides_ref = jsonobj['overrides'];
    for p in json_field_as_iterable(jsonobj, 'path'):
      p = prepare_path(p);
      self.regexes.append(re.compile("^" + re.escape(p) + "$"));
      self.regexes.append(re.compile("^" + re.escape(p) + "/"));
    for p in json_field_as_iterable(jsonobj, 'fnmatch'):
      p = prepare_path(p);
      self.regexes.append(re.compile(fnmatch.translate(p)));
    for p in json_field_as_iterable(jsonobj, 'regex'):
      self.regexes.append(re.compile(p));
    for p in json_field_as_iterable(jsonobj, 'glob'):
      p = prepare_path(p);
      self.regexes.append(re.compile(glob_to_regex.translate(p)));

# The 'none' component.
c_none = Component("none");

def get_components_from_jsonfh(f):
  """ reades a component description from the given json file. """
  jsonmap = json.load(f); #_
  res = { }; #:_
  for key in jsonmap.keys():
    if (not cr_compid.match(key)):
      raise ValueError("InvalidCompoIdentifier: The following is not a valid component identifier: " + key);
    if (key == "none"):
      raise ValueError("CompoNoneIdentifier: 'none' is not a valid component identifier");
    comp = Component(key);
    comp.fromJson(jsonmap[key]);
    res[key] = comp;
  for comp in res.values():
    if (len(comp.overrides_ref) != 0):
      if (comp.overrides_ref not in res):
        raise ValueError("OverriddenCompoInexistant: Overriden component '" + comp.overrides_ref
            + "' of component '" + comp.name + "' does not exist");
      comp.overrides = res[comp.overrides_ref];
  return res;

def get_component_of_file(compmap, fname):
  """ get the component of the given file. """
  may = set(); #_
  overridden = set(); #_
  for comp in compmap.values():
    for regex in comp.regexes:
      if (regex.match(fname)):
        may.add(comp);
        if (comp.overrides != None):
          overridden.add(comp.overrides);
        break;
  must = set(); #_
  must.update(may);
  for comp in overridden:
    must.discard(comp);
  if (len(must) > 1):
    raise ValueError("AmbiCompo: Component of file '" + fname + "' is ambiguous: Must be one of { "
        + ' '.join([ m.name for m in must]) + " }");
  if (len(must) < 1):
    return c_none;
  # There's only one element.
  return next(iter(must));

class CompoFilePair:
  __slots__ = (
    'compo',  # The component of the file.
    'file'    # The path to the file.
  );
  def __init__(self, compmap, fname):
    """ Constructs a CompoFilePair
        by determining the component of the given file
        from the given filename.
    """
    fname = prepare_path(fname);
    self.file = fname;
    self.compo = get_component_of_file(compmap, fname);

def get_compomap_from_args(nargs, usage):
  """ Returns the component map given via sys.argv, see usage(). """
  if (len(sys.argv) != nargs):
    usage();
    raise ValueError("InvNumArgs: Invalid number of arguments");
  specpath = sys.argv[1]; #:_
  compomap = None; #:_
  with open(specpath) as f:
    compomap = get_components_from_jsonfh(f);
  return compomap;

# ## #### #### ####
# Original main
# ## #### #### ####

def main():
  """ See usage() """
  compomap = get_compomap_from_args(2, usage); #:_
  for line in sys.stdin:
    fname = line.rstrip(); #:_
    cfp = CompoFilePair(compomap, fname); #:_
    print(cfp.compo.name + ":" + cfp.file);

# ## #### #### ####
# TODO additional mains ...
# ## #### #### ####

def usage_get_component_names():
  print (
"""
USAGE
  compogit-get-componentlist-of-filelist-from-compospec compospecjson < filelist

EXAMPLE
  find -type f | compogit-get-componentlist-of-filelist .compogit/compospec.json

DESCRIPTION
  Determines the component of the filepaths on STDIN and emits a list of component names.
  See also compogit-ann-components-to-filelist-given-compospec.

USAGE of compogit-ann-components-to-filelist-given-compospec:
""",
    file=sys.stderr
  );
  usage();

def get_component_name_list(compomap, linestream):
  """ Returns a list of touched components sorted alphabetically. """
  compos = set();
  for line in linestream:
    fname = line.rstrip(); #:_
    cfp = CompoFilePair(compomap, fname);
    compos.add(cfp.compo.name);
  compolist = list(compos);
  compolist.sort();
  return compolist;

def main_get_component_names():
  """ See usage usage_get_component_names() """
  compomap = get_compomap_from_args(2, usage_get_component_names); #:_
  compolist = get_component_name_list(compomap, sys.stdin); #:_
  for compo in compolist:
    print(compo);

def usage_filter():
  print (
"""
USAGE
  compogit-filter-filelist-for-component-given-compospec compospecjson component < filelist

EXAMPLE
  find -type f | compogit-get-componentlist-of-filelist .compogit/compospec.json Parser

DESCRIPTION
  Determines the component of the filepaths on STDIN and emits
  only those filepaths which are part of the given component.
  See also compogit-ann-components-to-filelist-given-compospec.

USAGE of compogit-ann-components-to-filelist-given-compospec:
""",
    file=sys.stderr
  );
  usage();

def main_filter():
  """ See usage usage_filter() """
  compomap = get_compomap_from_args(3, usage_filter); #:_
  componame = sys.argv[2]; #:_
  if componame not in compomap.keys():
    raise ValueError("UnknownComponent: \"" + componame + "\" does not identify a component");
  compo = compomap[componame]; #:_
  for line in sys.stdin:
    fname = line.rstrip(); #:_
    cfp = CompoFilePair(compomap, fname); #:_
    if compo == cfp.compo:
      print(cfp.file);
