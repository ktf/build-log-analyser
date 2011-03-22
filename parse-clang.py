#!/usr/bin/env python

from optparse import OptionParser
import re
from hashlib import md5

PAGE_HEADER="""<html><head><style>
ul  {
  font-size: 90%;
  margin-top: 4px;
}
h3 {
  margin-bottom: 2px;
}
h4 {
  margin-bottom: 4px;
  margin-top: 4px;
}

.count {
  font-size: 85%;
  font-style: italic;
}
.error_instances {
  margin-left: 25px;
}

.more {
  font-size: 90%;
  font-style: italic;
  padding-left: 25px;
  padding-bottom: 15px;
}
</style></head><body>"""

PAGE_FOOTER="""</body></html>
"""

def encodeHtml(s):
  return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

if __name__ == "__main__":
  parser = OptionParser()
  opts, args = parser.parse_args()
  if len(args) != 1:
    parser.error("Specify dump")
  filename = args[0] 
  f = open(filename) 
  count = 0
  line = encodeHtml(f.readline())
  state = {"current_package": None, "backtrace": []}
  error_index = {}
  while line:
    line = line.strip()
    if line.startswith(">> Compiling"):
      pass
    elif line.startswith("In file included"):
      newline = line.replace("In file included from ", "")
      state["backtrace"] += [newline.strip("\n")]
      if len(state["backtrace"]) == 1:
        state["compile_unit"] = newline
    elif "note:" in line:
      state["backtrace"] = []
    elif "warning:" in line:
      state["backtrace"] = []
    elif "error:" in line and not "bin/ld:" in line and not ".o'" in line:
      actual_error_location, error_message = line.split("error:",1)
      if "/src/" in actual_error_location:
        state["current_package"] = "/".join(actual_error_location.split("/src/")[1].split("/")[0:2])
      elif "/external/" in actual_error_location:
        state["current_package"] = "external package " + actual_error_location.split("/external/", 1)[1].split("/")[0]
      elif "/lcg/" in actual_error_location:
        state["current_package"] = "external package " + actual_error_location.split("/lcg/", 1)[1].split("/")[0]
      else:
        state["current_package"] = "generated file %s" % actual_error_location 

      if not error_message in error_index:
        error_index[error_message] = {}
      state["backtrace"].reverse()
      hasher = md5()
      actual_location_hasher = md5()
      actual_location_hasher.update(actual_error_location)
      for b in state["backtrace"]:
        hasher.update(b)
      backtrace_hash = hasher.hexdigest()
      actual_location_hash = actual_location_hasher.hexdigest()
      if not actual_location_hash in error_index[error_message]:
        error_index[error_message][actual_location_hash] = [
                                        state["current_package"].strip("\n"),
                                        actual_error_location.strip("\n"),
                                        state["compile_unit"].strip("\n"),
                                        {}]
      error_index[error_message][actual_location_hash][3][backtrace_hash] = state["backtrace"]
      state["backtrace"] = []
    count += 1
    line = encodeHtml(f.readline())
  print PAGE_HEADER
  # Sort by the number of paths involved
  errors = sorted(error_index.items(), key=lambda x : -sum([len(y[3]) for y in x[1].values()]))
  #errors = error_index.items()
  for k,v in errors:
    error_hash = md5(k)
    paths = sum([len(x[3]) for x in v.itervalues()])
    places = len(v.keys())
    print "<h3><a name='" + error_hash.hexdigest() + "' href='#" + error_hash.hexdigest() + "'>"
    print k + "</a></h3>"
    print "<span class='count'> (Found in " + str(paths) + " different path" + (paths-1 and "s" or "")
    print " of " +  str(places) + " different location" + (places-1 and "s" or "") + ")</span>"
    entries = sorted(x for x in v.itervalues())
    currentPackage = None
    print "<div class='error_instances'>"
    for x in entries:
      if x[0] != currentPackage:
        currentPackage = x[0]
        print "<h4>In " + currentPackage + "</h4>"
      print "<div>", x[1]
      backtraces = x[3].values()[0:3]
      for backtrace in backtraces:
        print "<ul>"
        style = ''
        for i in backtrace:
          print "<li " + style + ">Included by " + i + "</li>"
          style = 'style="list-style-type: none;"'
        print "</ul>" 
      if len(x[3]) > len(backtraces):
        print "<div class='more'>and " + str(len(x[3])-len(backtraces)) + " more include paths...</div>"
      print "</div>"
    print "</div>"
  print PAGE_FOOTER
