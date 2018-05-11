#!/usr/bin/env python
#
# Requires:
#  pip install PyGithub python-frontmatter
#

import difflib
import json
from optparse import OptionParser
import os
from os.path import abspath, dirname, exists, join, getmtime
import pprint
import time

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
except (AttributeError, ImportError):
    pass



yaml.SafeDumper.add_representer(collections.OrderedDict, dict_representer)
yaml.SafeDumper.add_representer(type(None), null_representer)
yaml.SafeLoader.add_constructor(_mapping_tag, dict_constructor)


def _parse(text, encoding, **defaults):
    text = frontmatter.u(text, encoding).strip()
    
    # metadata starts with defaults
    metadata = defaults.copy()
    
    try:
        _, fm, content = frontmatter.YAMLHandler.FM_BOUNDARY.split(text, 2)
    except ValueError:
        return metadata, text
    
    fm = yaml.safe_load(fm)
    
    if isinstance(fm, dict):
        fm.update(metadata)
        metadata = fm
        
    return metadata, content.strip()

def _loads(text, encoding='utf-8', handler=None, **defaults):
    metadata, content = _parse(text, encoding, **defaults)
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
        'powerup': 2018,
        'steamworks': 2017,
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
    
    
    def scan_all(self, scan_start):
        for team in range(scan_start, 7000):
            try:
                fm, _ = self.get_team_data(team)
            except IOError:
                print("Not found")
                continue
            
            # load frontmatter
            try:
                links = fm['team']['links']
            except KeyError:
                continue
            
            gh_page = links.get('GitHub')
            if not gh_page:
                gh_page = links.get('Github')
            if not gh_page:
                gh_page = links.get('github')
            
            if not gh_page:
                continue
            
            # if it has a github page, then call the thing
            data, guesses = self.process(gh_page, team)
            p.add_guesses_to_page(team, data, guesses, False)
    
    def _get_org_or_user(self, name):
        
        cache_file = join(self.cache_path, '%s.json' % name.lower())
        
        if exists(cache_file):
            
            # if the cache is older than a week, reload
            mtime = getmtime(cache_file)
            if time.time() - mtime < 60*60*24*7:
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
        'offseason',
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
        
    def process(self, name, team):
        
        team_data = None
        if team:
            team_data, team_path = self.get_team_data(team)
        
        name = name.replace('https://github.com/', '').split('/')[0]
        data = self._get_org_or_user(name)
        
        print("GitHub:", data['html_url'])
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
                    # if it can't guess and the data does not already exist, ask user
                    # -> so check if it exists
                    if team_data and 'robot_code' in team_data.metadata:
                        found = False
                        urls = set([vvv['html_url'] for vvv in vv])
                        for td_year, ydata in team_data['robot_code'].items():
                            if td_year != year:
                                continue
                            for td_data in ydata:
                                for td_type, tdt_data in td_data.items():
                                    if td_type == ctype and tdt_data[0] in urls:
                                        found = True
                                        break
                        if found:
                            break
                    
                    print("WARN: Could not guess! (%s %s)" % (year, ctype))
                    
                    for i, vvv in enumerate(vv):
                        print('%s: %s / %s / %s' % (i, vvv['html_url'], vvv['description'], vvv['language']))
                        
                    choice = choose_n(len(vv)-1)
                    if choice is not None:
                        vv[:] = [vv[choice]]
                    else:
                        vv[:] = []
        
        return data, guesses
    
    def get_team_data(self, team):
        p = 'frc%04d' % (int(int(team)/1000)*1000)
        sp = '%03d' % (int(int(team)/100)*100)
        
        team_path = abspath(join(dirname(__file__), '..', p, '_frc', sp, '%s.md' % team))
        print("Path:", team_path)
    
        fm = frontmatter.load(team_path)
        return fm, team_path
    
    def add_guesses_to_page(self, team, data, guesses, doit):
    
        fm, team_path = self.get_team_data(team)
        
        fm['team']['links']['GitHub'] = data['html_url']
        if 'Github' in fm['team']['links']:
            del fm['team']['links']['Github']
        if 'github' in fm['team']['links']:
            del fm['team']['links']['github']
        
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
                    with open(team_path) as fp:
                        old_contents = fp.read()
                    
                    print("Would write to file:")
                    print(old_contents)
                    print(fcontents)
                    
                    print("Diff")
                    for line in difflib.unified_diff(old_contents.splitlines(), fcontents.splitlines(),
                                                     fromfile='old_contents', tofile='new_contents'):
                        print(line)
                    
                    doit = yesno("Write it?")
                    
                if doit:
                    print("Writing to file")
                    
                    with open(team_path, 'w') as fp:
                        fp.write(fcontents)
                        
                    if yesno("Edit it?"):
                        os.system('"%s" "%s"' % (os.environ.get("EDITOR", "vi"), team_path))
            else:
                print("No changes detected")

if __name__ == '__main__':
    
    parser = OptionParser("%prog REPO [TEAM]")
    
    parser.add_option('--scan', default=None, action='store_true', help="Update all teams")
    parser.add_option('--scan-start', default=1, type=int)
    parser.add_option('--doit', default=False, action='store_true', help='Actually write results to disk')
    
    options, args = parser.parse_args()
    
    if len(args) == 1:
        name = args[0]
        team = None
    elif len(args) == 2:
        name = args[0]
        team = args[1]
    elif not options.scan:
        parser.error("must specify a repo")
        exit(1)
    
    cache_path = abspath(join(dirname(__file__), '.cache'))
    p = Processor(cache_path)
    
    if options.scan:
        p.scan_all(options.scan_start)
    else:
        data, guesses = p.process(name, team)

        if team:
            p.add_guesses_to_page(team, data, guesses, options.doit)
        
