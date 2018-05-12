#!/usr/bin/env python

from collections import OrderedDict
import csv
import sys

import os
from os.path import abspath, dirname, exists, join

import optparse

import frontmatter
import code_from_gh
import yaml

def read_team_csv(csv_fname):
    with open(csv_fname) as fp:
        reader = csv.reader(fp)
        for row in reader:
            yield [r.strip() for r in row]

def add_maybe(d, f, v):
    if not v:
        if f not in d:
            d[f] = None
    else:
        d[f] = v

def add_maybe_web(d, k, nv):
    if nv:
        v = d.get(k)
        if v is None or v.lower().strip('/') != nv.lower().strip('/'):
            d[k] = nv

def main():

    # input is teams csv datafile from TBA
    # -> https://github.com/the-blue-alliance/the-blue-alliance-data
    csv_fname = abspath(sys.argv[1])
    max_team = int(sys.argv[2])
    mode = sys.argv[3]
    
    if mode not in ['new', 'update']:
        print("Error: invalid mode")
        return

    os.chdir(abspath(join(dirname(__file__), '..')))
    cwd = os.getcwd()
    
    for row in read_team_csv(csv_fname):
        # this changes on occasion...
        number, name, sponsors, l1, l2, l3, website, rookie_year, \
            facebook, twitter, youtube, github, instagram, periscope = row
        
        name = name
        rookie_year = rookie_year
        
        if rookie_year:
            rookie_year = int(rookie_year)
        
        number = number[3:]
        if int(number) > max_team:
            continue
        
        d1 = '%04d' % (int(int(number)/1000)*1000,)
        d2 = '%03d' % (int(int(number)/100)*100,)
        
        f = join(cwd, 'frc%s' % d1, '_frc', d2, '%s.md' % number)
        
        if mode == 'new' and exists(f):
            continue
        
        if 'firstinspires' in website:
            website = ''
        
        if l3:
            location = '%s, %s, %s' % (l1, l2, l3)
        elif l2:
            location = '%s, %s' % (l1, l2)
        else:
            location = l1
            
        sponsors = [s.strip() for s in sponsors.split('/')]
        if sponsors == ['']:
            sponsors = None
        else:
            if '&' in sponsors[-1]:
                sN = sponsors[-1].split('&')
                del sponsors[-1]
                sponsors += [s.strip() for s in sN]
        
        if mode == 'update':
            try:
                fm = frontmatter.load(f)
            except:
                print("Error at %s" % f)
                raise
                
            reformatted = str(frontmatter.dumps(fm))
            
            if 'team' not in fm.metadata:
                raise Exception("Error in %s" % f)
                
            team = fm.metadata['team']
            if 'links' not in fm.metadata['team']:
                links = OrderedDict()
            else:
                links = fm.metadata['team']['links']
        else:
            data = OrderedDict()
            team = OrderedDict()
            links = OrderedDict()
            
            data['title'] = 'FRC Team %s' % number
            data['team'] = team
            
            team['type'] = 'FRC'
            team['number'] = int(number)
        
        add_maybe(team, 'name', name)
        add_maybe(team, 'rookie_year', rookie_year)
        add_maybe(team, 'location', location)
        
        if sponsors and mode != 'update':
            team['sponsors'] = sponsors
        
        if 'Github' in links:
            links['GitHub'] = links['Github']
            del links['Github']
        
        add_maybe_web(links, 'Website', website)
        add_maybe_web(links, 'Facebook', facebook)
        add_maybe_web(links, 'Twitter', twitter)
        add_maybe_web(links, 'YouTube', youtube)
        add_maybe_web(links, 'GitHub', github)
        add_maybe_web(links, 'Instagram', instagram)
        add_maybe_web(links, 'Periscope', periscope)
        
        if mode == 'update':
            
            if links:
                fm.metadata['team']['links'] = links
            
            if fm.content.strip() == 'No content has been added for this team':
                fm.content = '{% include remove_this_line_and_add_a_paragraph %}'
            
            page = str(frontmatter.dumps(fm))
            if reformatted == page:
                # don't make gratuitious changes
                continue
        
        elif mode == 'new':
            
            if links:
                team['links'] = links
        
            page = '---\n%s\n---\n\n{%% include remove_this_line_and_add_a_paragraph %%}\n' % (
                yaml.safe_dump(data)
            )
            
            # roundtrip through frontmatter to get the formatting consistent
            page = frontmatter.dumps(frontmatter.loads(page))
            
        if not exists(dirname(f)):
            os.makedirs(dirname(f))
            
        with open(f, 'w') as fp:
            fp.write(page)

if __name__ == '__main__':
    main()
