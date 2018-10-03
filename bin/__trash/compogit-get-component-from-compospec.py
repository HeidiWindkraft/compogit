#!/usr/bin/env python3
# See usage().

import sys;
import re;
import json;
import fnmatch;

def usage():
  print (
"""
SYNOPSIS
  compogit-get-component-from-compospec compospecjson < filelist

EXAMPLE
  find -type f | compogit-get-component-from-compospec .compogit/compospec.json

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
        - 'glob': A list of glob patterns (currently not supported).
        - 'regex': A list of regular expressions.
    - 'overrides': The component which is overriden by this component (optional).
                   If the path expressions of multiple components match, then
                   a component A which overrides another component B
                   takes precedence over the other component B.
                   If both A and B match for a file, this file is in component A.
""",
    file=sys.stderr
  );


#### #### #### #### #### #### #### #### #### #### #### ####
# Implementation of glob.
#### #### #### #### #### #### #### #### #### #### #### ####

# The pattern you get when you pass "**" or "*" to fnmatch.translate.
g_doublestarpat = None;
g_singlestarpat = None;

def init_glob_starpats():
  """ Lazily initializes the star patterns.
      "**" and "*" can be matched to the same pattern,
      but why would anyone do that?
      Just to optimize the case that someone wrongly thought that fnmatch had "**"?
  """
  global g_doublestarpat;
  global g_singlestarpat;
  if (g_doublestarpat == None):
    angle = re.compile(".*<([^\\\\>]+)\\\\?>"); #:_
    g_doublestarpat = angle.match(fnmatch.translate("<**>")).group(1);
    g_singlestarpat = angle.match(fnmatch.translate("<*>")).group(1);
    if (g_doublestarpat == g_singlestarpat):
      raise Exception("Feature 'glob' does not work. Unexpected fnmatch implementation.");
  return;

def translate_glob(glob):
  """ Translates a glob pattern to a regex pattern. """
  pat = fnmatch.translate(glob); #:_
  # Note:
  #  - '<' and '>' must not appear in filenames.
  #  - No glob/fnmatch pattern can result in regex /\.*/.
  init_glob_starpats();
  pat = pat.replace(g_doublestarpat, "<>");
  pat = pat.replace(g_singlestarpat, "[^/]*");
  pat = pat.replace("<>", ".*");
  return pat;
  # pat = re.escape(glob); #:_
  # # Care about unix character set rules.
  # #  pat = re.sub(r"\\\[([^\\]+)\]", r"[\1]", pat); # inverted set, like [!a-z].
  # #  pat = re.sub(r"\\\[([^\\]+)\]", r"[\1]", pat); # normal set, like [a-z].
  # # Care about common rules.
  # pat = pat.replace("\\?", "."); # ? matches a single character.
  # pat = pat.replace("\\*\\*", ".*"); # ** matches all files including files in sub-directories.
  # pat = pat.replace("\\*", "[^/]*"); # * matches all files in this directory.


#### #### #### #### #### #### #### #### #### #### #### ####
# Implementation of compogit-get-component-from-compospec.
#### #### #### #### #### #### #### #### #### #### #### ####

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
  if (field == None): # TODO json doesn't do this
    # Field is None -> empty list.
    return [];
  elif (isinstance(field,str)):
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
      self.regexes.append(re.compile(translate_glob(p)));
      # raise ValueError("In component " + self.name + ": glob is currently not supported."); # TODO

# The 'none' component.
c_none = Component("none");

def get_components_from_jsonfh(f):
  """ reades a component description from the given json file. """
  jsonmap = json.load(f); #_
  res = { }; #:_
  for key in jsonmap.keys():
    if (key in res): # TODO json doesn't do this.
      raise ValueError("MultipleCompoDefs: Multiple definitions of '" + key + "' in component description");
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
  # There's only one element. for comp in must: return comp; # TODO bad coverage
  return next(iter(must));

class CompoFilePair:
  __slots__ = (
    'compo',  # The component of the file.
    'file'    # The path to the file.
  );
  def __init__(self, compmap, fname):
    """ Constructs a CompFilePair
        by determining the component of the given file
        from the given filename.
    """
    fname = prepare_path(fname);
    self.file = fname;
    self.compo = get_component_of_file(compmap, fname);

def main():
  """ See usage() """
  if (len(sys.argv) != 2):
    usage();
    raise ValueError("InvNumArgs: Invalid number of arguments");
  specpath = sys.argv[1]; #:_
  compomap = None; #:_
  with open(specpath) as f:
    compomap = get_components_from_jsonfh(f);
  for line in sys.stdin:
    fname = line.rstrip(); #:_
    cfp = CompoFilePair(compomap, fname); #:_
    print(cfp.compo.name + ":" + cfp.file);

if __name__ == "__main__":
  main();
