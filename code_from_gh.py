#!/usr/bin/env python
#
# Requires:
#  pip install PyGithub python-frontmatter
#

import json
from optparse import OptionParser
import os
from os.path import abspath, dirname, exists, join
import pprint
import sys

import github
import frontmatter

#
# Begin terrible hack
#


# Change YAML to load/save in correct order
# - From http://stackoverflow.com/a/21048064/5483904

import collections
import yaml

_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG


def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())

def dict_constructor(loader, node):
    loader.flatten_mapping(node)
    return collections.OrderedDict(loader.construct_pairs(node))

def null_representer(dumper, value):
    return dumper.represent_scalar(u'tag:yaml.org,2002:null', '')

try:
    yaml.CSafeDumper.add_representer(collections.OrderedDict, dict_representer)
    yaml.CSafeDumper.add_representer(type(None), null_representer)
except ImportError:
    pass



yaml.SafeDumper.add_representer(collections.OrderedDict, dict_representer)
yaml.SafeDumper.add_representer(type(None), null_representer)
yaml.SafeLoader.add_constructor(_mapping_tag, dict_constructor)


def _parse(text, **defaults):
    text = frontmatter.u(text)
    
    # metadata starts with defaults
    metadata = defaults.copy()
    
    try:
        _, fm, content = frontmatter.FM_BOUNDARY.split(text, 2)
    except ValueError:
        return metadata, text
    
    fm = yaml.safe_load(fm)
    
    if isinstance(fm, dict):
        fm.update(metadata)
        metadata = fm
        
    return metadata, content.strip()

def _loads(text, **defaults):
    metadata, content = _parse(text, **defaults)
    post = frontmatter.Post(content)
    post.metadata = metadata
    return post

frontmatter.parse = _parse
frontmatter.loads = _loads

#
# End terrible hack
#

def yesno(prompt):
    while True:
        v = input("%s [Y/N]? " % prompt).lower()
        if v in ['y', 'yes']:
            return True
        elif v in ['n', 'no']:
            return False 

def choose_n(n):
    while True:
        try:
            v = input('[0-%d] ' % n)
            if v == '':
                return None
            return int(v)
        except ValueError:
            pass

def normalize(w):
    return w.replace('-', ' ').replace('_', ' ').lower()

class Processor:
    
    game_mapping = {
        'stronghold': 2016,
        'recycle rush': 2015,
        'aerial assist': 2014,
        'ultimate ascent': 2013,
        'rebound rumble': 2012,
        'logomotion': 2011,
        'breakaway': 2010,
        'lunacy': 2009,
        'overdrive': 2008,
        'rack n roll': 2007,
        'aim high': 2006,
        # anything older than this probably doesn't exist on github...
    }
    
    games = list(game_mapping.keys())
    for game in games:
        if ' ' in game:
            g = game.replace(' ', '')
            games.append(g)
            game_mapping[g] = game_mapping[game]
    
    years = list(map(str, game_mapping.values()))
    
    def __init__(self, cache_path):
        self.gh = github.Github(login_or_token=os.environ['GITHUB_TOKEN'])
        self.cache_path = cache_path
    
    
    def _get_org_or_user(self, name):
        
        cache_file = join(self.cache_path, '%s.json' % name.lower())
        
        if exists(cache_file):
            with open(cache_file, 'r') as fp:
                return json.load(fp)
       
        try:
            org = self.gh.get_organization(name)
        except github.GithubException as e:
            if e.status != 404:
                raise
            org = self.gh.get_user(name)
       
        repos = []
        data = {
            'html_url': org.html_url,
            'blog': org.blog,
            'name': org.name,
            'repos': repos 
        }
        
        for repo in org.get_repos():
            repos.append({
                'name': repo.name,
                'html_url': repo.html_url,
                'description': repo.description or '',
                'language': repo.language,
            })
        
        with open(cache_file, 'w') as fp:
            json.dump(data, fp, sort_keys=True,
                      indent=4, separators=(',', ': '))
            
        return data
        
    
    vision_keywords = ['vision', 'image', 'img', 'camera', 'target', 'track']
    ui_keywords = ['dashboard', 'driver station', 'ui']
    scouting_keywords = ['scouting']
        
    def guess_type(self, name, desc):
        
        if 'robot code' in name or 'robot code' in desc:
            return 'Robot'
        
        for kw in self.scouting_keywords:
            if kw in name or kw in desc:
                return 'Scouting'
        
        for kw in self.vision_keywords:
            if kw in name or kw in desc:
                return 'Vision'
        
        for kw in self.ui_keywords:
            if kw in name or kw in desc:
                return 'Dashboard'
        
        # No guess? Default to robot code...
        return 'Robot'
    
    filter_words = [
        'practice',
        'testing',
        'website',
        'sample',
        'beta',
        'ftc'
    ]
    
    
    
    def filter_false_positives(self, repo):
        name = normalize(repo['name'])
        desc = normalize(repo['description'])
        
        for word in self.filter_words:
            if word in name or word in desc:
                return False
            
        return True
        
    def process(self, name):
        
        data = self._get_org_or_user(name)
        
        print("Github:", data['html_url'])
        print("Website:", data['blog'])
        
        # year: {type: [repos]}
        guesses = {}
        
        for repo in data['repos']:
        
            name = normalize(repo['name'])
            desc = normalize(repo['description'])
            
            print("-> '%s': '%s' (%s)" % (name, desc, repo['language']))
        
            # find things with 'year' in them... 2014, 2015, 2016
            for year in self.years:
                if year in name or year in desc:
                    codetype = self.guess_type(name, desc)
                    
                    guesses.setdefault(int(year), {}) \
                           .setdefault(codetype, []).append(repo)
                    print("  found as", year)
                    break
            else:
                # find things with game names in them
                for game in self.games:
                    if game in name or game in desc:
                        codetype = self.guess_type(name, desc)
                        year = self.game_mapping[game]
                        
                        guesses.setdefault(year, {}) \
                               .setdefault(codetype, []).append(repo)
                        
                        print("  found as", game, '(%s)' % year)
                        break
        
        print()
        
        # if there are duplicates per year, then filter via specific keywords
        for year, v in guesses.items():
            for ctype, vv in v.items():
                if len(vv) <= 1:
                    continue
                
                vv[:] = filter(self.filter_false_positives, vv)
                if len(vv) > 1:
                    # if it can't guess, ask user
                    print("WARN: Could not guess! (%s %s)" % (year, ctype))
                    
                    for i, vvv in enumerate(vv):
                        print('%s: %s / %s / %s' % (i, vvv['html_url'], vvv['description'], vvv['language']))
                        
                    choice = choose_n(len(vv)-1)
                    if choice is not None:
                        vv[:] = [vv[choice]]
                    else:
                        vv[:] = []
        
        return data, guesses
    
    def add_guesses_to_page(self, team, data, guesses, doit):
    
        p = 'frc%04d' % (int(int(team)/1000)*1000)
        sp = '%03d' % (int(int(team)/100)*100)
        
        team_path = abspath(join(dirname(__file__), '..', p, '_frc', sp, '%s.md' % team))
        print("Path:", team_path)
    
        fm = frontmatter.load(team_path)
        
        fm['team']['links']['Github'] = data['html_url']
        
        if data['blog']:
            fm['team']['links']['Website'] = data['blog']
        
        if guesses:
            robot_code = fm.metadata.setdefault('robot_code', collections.OrderedDict())
            need_sort = False
            changed = False
            
            for year in sorted(guesses.keys()):
                types = guesses[year]
                iyear = int(year)
                
                need_sort = need_sort or iyear not in robot_code
                
                existing = None
                                
                for ctype in sorted(types.keys()):
                    # should only be one of each type
                    repos = types[ctype]
                    if not repos:
                        continue
                    
                    # Don't create until we have to
                    if existing is None:
                        existing = robot_code.setdefault(iyear, [collections.OrderedDict()])
                        existing_types = existing[0]
                
                    
                    repo = repos[0]
                    
                    # if the type already exists, and URL is different, output a warning, but do not change
                    existing_type = existing_types.get(ctype)
                    if existing_type:
                        if existing_type[0] != repo['html_url']:
                            pass
                    
                        # if the URL already exists, then don't change the language
                    else:
                        # if it doesn't exist, set it
                        existing_types[ctype] = [repo['html_url'], repo['language']]
                        changed = True
        
            if need_sort:
                fm.metadata['robot_code'] = collections.OrderedDict(sorted((k, v) for k, v in robot_code.items()))
                
            if changed:
                # write it out to file
                fcontents = frontmatter.dumps(fm)
                
                if not doit:
                    print("Would write to file:")
                    print(fcontents)
                    
                    doit = yesno("Write it?")
                    
                if doit:
                    print("Writing to file")
                    
                    with open(team_path, 'w') as fp:
                        fp.write(fcontents)
            else:
                print("No changes detected")
        #pprint.pprint(fm)
    
        # determine team number
        # find page
        # read existing front matter
        # if it already exists, don't replace it!
        
        # populate website if org has website
        # populate github link
        
        # populate robot_code with guesses
        
if __name__ == '__main__':
    
    parser = OptionParser("%prog REPO [TEAM]")
    
    parser.add_option('--doit', default=False, action='store_true', help='Actually write results to disk')
    
    options, args = parser.parse_args()
    
    
    if len(args) == 1:
        name = args[0]
        team = None
    elif len(args) == 2:
        name = args[0]
        team = args[1]
    else:
        parser.error("must specify a repo")
        exit(1)
    
    cache_path = abspath(join(dirname(__file__), '.cache'))
    p = Processor(cache_path)
    
    name = sys.argv[1]
    data, guesses = p.process(name)

    if team:
        p.add_guesses_to_page(team, data, guesses, options.doit)
    