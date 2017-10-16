#!/usr/bin/env python3

import yaml
import os
import sys
import re

license = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""

baseyaml = """
openapi: 3.0.0
info:
  version: 1.0.0
  description: This is the API specifications for interacting with the Kibble UI.
  title: Apache Kibble API
  license:
    name: Apache 2.0
    url: 'http://www.apache.org/licenses/LICENSE-2.0.html'
"""

bpath = os.path.dirname(os.path.abspath(__file__))


def deconstruct():
    yml = yaml.load(open(bpath + "/../openapi.yaml"))
    noDefs = 0
    print("Dumping paths into pages...")
    for endpoint, defs in yml['paths'].items():
        noDefs += 1
        xendpoint = endpoint.replace("/api/", "")
        ypath = os.path.abspath("%s/../../pages/%s.py" % (bpath, xendpoint))
        print(ypath)
        if os.path.isfile(ypath):
            print("Editing %s" % ypath)
            contents = open(ypath, "r").read()
            contents = re.sub(r"^([#\n](?!\s*\"\"\")[^\r\n]*\n?)+", "", contents, re.MULTILINE)
            odefs = yaml.dump(defs, default_flow_style=False)
            odefs = "\n".join(["# %s" % line for line in odefs.split("\n")])
            with open(ypath, "w") as f:
                f.write(license)
                f.write("########################################################################\n")
                f.write("# OPENAPI-URI: %s\n" % endpoint)
                f.write("########################################################################\n")
                f.write(odefs)
                f.write("\n########################################################################\n")
                f.write("\n\n")
                f.write(contents)
                f.close()
        
    print("Dumping security components...")
    for basetype, bdefs in yml['components'].items():
        for schema, defs in bdefs.items():
            noDefs += 1
            ypath = "%s/components/%s/%s.yaml" % (bpath, basetype, schema)
            ydir = os.path.dirname(ypath)
            if not os.path.isdir(ydir):
                print("Making directory %s" % ydir)
                os.makedirs(ydir, exist_ok = True)
            with open(ypath, "w") as f:
                f.write("########################################################################\n")
                f.write("# %-68s #\n" % defs.get('summary', schema))
                f.write("########################################################################\n")
                f.write(yaml.dump(defs, default_flow_style=False))
                f.close()
    print("Dumped %u definitions." % noDefs)
    
def construct():
    yml = {}
    yml['paths'] = {}
    yml['components'] = {}
    apidir = os.path.abspath("%s/../../pages/" % bpath)
    print("Scanning %s" % apidir)
    for d in os.listdir(apidir):
        cdir = os.path.abspath("%s/%s" % (apidir, d))
        if os.path.isdir(cdir):
            print("Scanning %s" % cdir)
            for fname in os.listdir(cdir):
                if fname.endswith(".py"):
                    fpath = "%s/%s" % (cdir, fname)
                    print("Scanning %s" % fpath)
                    contents = open(fpath, "r").read()
                    m = re.search(r"OPENAPI-URI: (\S+)\n##+\n([\s\S]+?)##+", contents)
                    if m:
                        apath = m.group(1)
                        cyml = m.group(2)
                        print("Weaving in API path %s" % apath)
                        cyml = "\n".join([line[2:] for line in cyml.split("\n")])
                        defs = yaml.load(cyml)
                        yml['paths'][apath] = defs
        else:
            fname = d
            if fname.endswith(".py"):
                fpath = "%s/%s" % (apidir, fname)
                print("Scanning %s" % fpath)
                contents = open(fpath, "r").read()
                m = re.search(r"OPENAPI-URI: (\S+)\n##+\n([\s\S]+?)##+", contents)
                if m:
                    apath = m.group(1)
                    cyml = m.group(2)
                    print("Weaving in API path %s" % apath)
                    cyml = "\n".join([line[2:] for line in cyml.split("\n")])
                    defs = yaml.load(cyml)
                    yml['paths'][apath] = defs
    apidir = os.path.abspath("%s/components" % bpath)
    print("Scanning %s" % apidir)
    for d in os.listdir(apidir):
        cdir = os.path.abspath("%s/%s" % (apidir, d))
        if os.path.isdir(cdir):
            print("Scanning %s" % cdir)
            for fname in os.listdir(cdir):
                if fname.endswith(".yaml"):
                    yml['components'][d] = yml['components'].get(d, {})
                    fpath = "%s/%s" % (cdir, fname)
                    print("Scanning %s" % fpath)
                    defs = yaml.load(open(fpath))
                    yml['components'][d][fname.replace(".yaml", "")] = defs
    ypath = os.path.abspath("%s/../openapi.yaml" % bpath)
    with open(ypath, "w") as f:
        f.write(baseyaml)
        f.write(yaml.dump(yml, default_flow_style=False))
        f.close()
    print("All done!")
    
if len(sys.argv) > 1 and sys.argv[1] == 'deconstruct':
    deconstruct()
else:
    construct()