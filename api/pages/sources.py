#!/usr/bin/env python3
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
This is the source list handler for Kibble
"""

import json
import re
import time
import hashlib

def canModifySource(session):
    """ Determine if the user can edit sources in this org """
    if session.user['userlevel'] == 'admin':
        return True
    
    dOrg = session.user['defaultOrganisation'] or "apache"
    if session.DB.ES.exists(index=session.DB.dbname, doc_type="org", id= dOrg):
        xorg = session.DB.ES.get(index=session.DB.dbname, doc_type="org", id= dOrg)['_source']
        if session.user['email'] in xorg['admins']:
            return True

def run(API, environ, indata, session):
    
    # We need to be logged in for this!
    if not session.user:
        raise API.exception(403, "You must be logged in to use this API endpoint! %s")
    
    method = environ['REQUEST_METHOD']
    
    if method in ['GET', 'POST']:
        # Fetch organisation data
        dOrg = session.user['defaultOrganisation'] or "apache"
        if session.DB.ES.exists(index=session.DB.dbname, doc_type="organisation", id= dOrg):
            org = session.DB.ES.get(index=session.DB.dbname, doc_type="organisation", id= dOrg)['_source']
            del org['admins']
        else:
            raise API.exception(404, "No such organisation, '%s'" % dOrg)
        
        sourceTypes = indata.get('types', [])
        # Fetch all sources for default org
        
        res = session.DB.ES.search(
                index=session.DB.dbname,
                doc_type="source",
                size = 5000,
                body = {
                    'query': {
                        'term': {
                            'organisation': dOrg
                        }
                    }
                }
            )
        
        # Secondly, fetch the view if we have such a thing enabled
        viewList = []
        if indata.get('view'):
            if session.DB.ES.exists(index=session.DB.dbname, doc_type="view", id = indata['view']):
                view = session.DB.ES.get(index=session.DB.dbname, doc_type="view", id = indata['view'])
                viewList = view['_source']['sourceList']
        
        
        sources = []
        for hit in res['hits']['hits']:
            doc = hit['_source']
            if viewList and not doc['sourceID'] in viewList:
                continue
            if sourceTypes and not doc['type'] in sourceTypes:
                continue
            if indata.get('quick'):
                xdoc = {
                    'sourceID': doc['sourceID'],
                    'type': doc['type'],
                    'sourceURL': doc['sourceURL']
                    }
                sources.append(xdoc)
            else:
                sources.append(doc)
        
        JSON_OUT = {
            'sources': sources,
            'okay': True,
            'organisation': org
        }
        yield json.dumps(JSON_OUT)
        return
    
    # Add one or more sources
    if method == "PUT":
        if canModifySource(session):
            new = 0
            old = 0
            for source in indata.get('sources', []):
                sourceURL = source['sourceURL']
                sourceType = source['type']
                creds = {}
                if 'username' in source and len(source['username']) > 0:
                    creds['username'] = source['username']
                if 'password' in source and len(source['password']) > 0:
                    creds['password'] = source['password']
                if 'cookie' in source and len(source['cookie']) > 0:
                    creds['cookie'] = source['cookie']
                sourceID = hashlib.sha224( ("%s-%s" % (sourceType, sourceURL)).encode('utf-8') ).hexdigest()
                
                dOrg = session.user['defaultOrganisation'] or "apache"
                
                doc = {
                    'organisation': dOrg,
                    'sourceURL': sourceURL,
                    'sourceID': sourceID,
                    'type': sourceType,
                    'creds': creds,
                    'steps': {}
                }
                if session.DB.ES.exists(index=session.DB.dbname, doc_type="source", id = sourceID):
                    old += 1
                else:
                    new += 1
                session.DB.ES.index(index=session.DB.dbname, doc_type="source", id = sourceID, body = doc)
            yield json.dumps({
                "message": "Sources added/updated",
                "added": new,
                "updated": old
                })
        else:
            raise API.exception(403, "You don't have prmission to sources to this organisation.")
    
    # Delete a source
    if method == "DELETE":
        if canModifySource(session):
            sourceID = indata.get('id')
            if session.DB.ES.exists(index=session.DB.dbname, doc_type="source", id = sourceID):
                # Delete all data pertainig to this source
                session.DB.ES.delete_by_query(index=session.DB.dbname, body = {'query': {'match': {'sourceID': sourceID}}})
                yield json.dumps({'message': "Source deleted"})
            else:
                raise API.exception(404, "No such source item")
        else:
            raise API.exception(403, "You don't have prmission to delete this source.")
        
    # Edit a source
    if method == "PATCH":
        pass
