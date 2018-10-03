#!/usr/bin/env python3
# See usage.

import sys;
import re;

def usage():
  print (
"""
SYNOPSIS
  glob_to_regex "globpattern"

EXAMPLE
  glob_to_regex "*.txt"
  > ^[^\\/]*\\.txt$
  glob_to_regex "a/**/*.txt"
  > ...

DESCRIPTION
  Converts a glob pattern to a regex pattern.
""",
    file=sys.stderr
  );

special_regex_chars = {"^", "=", "|", "!", ".", "(", ")", "$", "+"};

re_anysubdir = re.compile(r"^(/+\*\*+/+)");

STATE_IN_TEXT=0
STATE_IN_CHARSET=1
STATE_IN_GROUP=2

def handle_backslashes(glob, begin):
  """ Process backslashes in a glob pattern. """
  i = begin; #:int
  count = 0; #:int
  s = len(glob); #:int
  while (i < s):
    c = glob[i]; #:_
    if (c == "\\"):
      count += 1;
    else:
      break;
    i += 1;
  # If there's an odd number of backslashes, the last backslash escapes the subsequent char.
  if ((count % 2) == 1):
    if (i == s):
      raise ValueError("EndOnOddBackslash: Odd number of backslashes at the end of a glob pattern \"" + glob + "\"");
    i += 1;
  return (i, glob[begin:i]);

def handle_star(glob, begin):
  """ Process stars in a glob pattern - except "/**/". """
  i = begin; #:int
  count = 0; #:int
  s = len(glob); #:int
  while (i < s):
    c = glob[i]; #:_
    if (c == "*"):
      count += 1;
    else:
      break;
    i += 1;
  # Handle '*' pattern.
  if (count == 1):
    return (i, "[^\\/]*");
  # Handle '**' pattern.
  return (i, ".*");


def translate(glob):
  """ Translate the glob pattern given as string `glob` to a regex pattern (returned as string). """
  i = 0; #:int
  s = len(glob); #:int
  buf = [ "^" ]; #:_
  states = [ STATE_IN_TEXT ]; #:_
  while (i < s):
    c = glob[i]; #:_

    # Handle potential state changes:
    # Handle character sets like "[a-z]" and "[!a-z]".
    if (c == "["):
      if (states[-1] == STATE_IN_CHARSET):
        raise ValueError("InvCsBegin: Cannot nest charset begin '[' in char set of glob pattern \"" + glob + "\"");
      states.append(STATE_IN_CHARSET);
      buf.append("[");
      j = i + 1; #:_
      if (j < s):
        d = glob[j];
        if (d == "!"):
          buf.append("^");
          i += 1;
    elif (c == "]"):
      if (states[-1] != STATE_IN_CHARSET):
        raise ValueError("InvCsEnd: Encountered ']' without matching '[' in glob pattern \"" + glob + "\"");
      states.pop();
      buf.append("]");
    # Handle groups.
    elif (c == "{"):
      if (states[-1] != STATE_IN_TEXT):
        raise ValueError("InvGrpBegin: Cannot start a group ('{') in outside of normal text in glob pattern \"" + glob + "\"");
      states.append(STATE_IN_GROUP);
      buf.append("(");
    elif (c == "}"):
      if (states[-1] != STATE_IN_GROUP):
        raise ValueError("InvGrpEnd: Encountered '}' without matching '{' in glob pattern \"" + glob + "\"");
      states.pop();
      buf.append(")");

    # Handle other characters:
    # Escape special regex characters.
    elif (c in special_regex_chars):
      buf.append("\\" + c);
    # Handle forward slashes. They are path separators.
    elif (c == "/"):
      # "/**/" is a special case, which is also allowed to match "/".
      m = re_anysubdir.match(glob[i:]); #:_;
      if (m):
        buf.append("(\\/|\\/.*\\/)");
        matched = m.group(1);
        i += len(matched) - 1;
      else:
        buf.append("\\/");
    # Handle back slashes. They aren't path separators.
    #  "\\" is one backslash.
    #  "\" escapes a subsequent character.
    elif (c == "\\"):
      to_append = ""; #:str
      end = 0; #:int
      (end, to_append) = handle_backslashes(glob, i);
      i = end - 1;
      buf.append(to_append);
    # ',' separates alternatives in groups. Otherwise just escape and append it.
    elif (c == ","):
      if (states[-1] == STATE_IN_GROUP):
        buf.append("|");
      else:
        buf.append("\\,");
    # '?' matches everything except '/'.
    elif (c == "?"):
      buf.append("[^\\/]");
    # '*' can either be a single star or the beginning of '**'.
    elif (c == "*"):
      to_append = ""; #:str
      end = 0; #:int
      (end, to_append) = handle_star(glob, i);
      i = end - 1;
      buf.append(to_append);
    # All other characters are just appended.
    else:
      buf.append(c);
    i += 1;
  # End of while loop.
  # Check whether we end in the correct state.
  if ((len(states) != 1) and (states[-1] != STATE_IN_TEXT)):
    raise ValueError("InvGlobEndState: Encountered unexpected end in glob pattern \"" + glob + "\"");
  # End regex pattern.
  buf.append("$");
  return ''.join(buf);

def main():
  """ See usage() """
  if (len(sys.argv) != 2):
    usage();
    raise ValueError("InvNumArgs: Invalid number of arguments");
  glob = sys.argv[1]; #:_
  print(translate(glob));

if __name__ == "__main__":
  main();
