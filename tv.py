#!/bin/env python3

import argparse
from typing import OrderedDict
import dateutil.tz
import requests
import re
import yaml

from datetime import datetime, timedelta, timezone
# from zoneinfo import ZoneInfo  # Need Python 3.9

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--html', action='store_true')
named_args, pos_args = arg_parser.parse_known_args()

with open('tv.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)
# print(config)

# tz = ZoneInfo(config['timezone_region'])  # Need Python 3.9
tz = dateutil.tz.gettz(config['timezone_region'])
region_id = config['freeview_region_id']

today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
command = ' '.join(pos_args).lower()

delta_days = 0
weekdays = [re.compile(regex) for regex in [
    r'mon', r'tue', r'wed', r'thu', r'fri', r'sat', r'sun'
]]

next_7 = []
for day_number in range(today.weekday() + 1, today.weekday() + 8):
    next_7.append(weekdays[day_number % 7])
range_days = None

if 'tomorrow' in command:
    delta_days = 1
elif 'yesterday' in command:
    delta_days = -1
elif 'next' in command:
    range_days = int(command.replace('next', ''))
else:
    for index, weekday in enumerate(next_7):
        if weekday.search(command):
            delta_days = index + 1
            break

season_episode_regex = re.compile(r's[a-z]* *([0-9]+)([, :]+)?e[a-z]* *([0-9]+)', re.IGNORECASE)

# Example synopsis that starts with episode name:
# "Cantilevers & Lifts. Secrets of a New York skyscraper that defies the laws of physics. The ..."
# Assume that a short first sentence is an episode name:
episode_title_regex = re.compile(r'^[^.?!:]{1,40}[.?!:]')
not_episode_title_regex = re.compile(r'\b(series|show|documentary)\b', re.IGNORECASE)

channel_ignore = [re.compile(regex, re.IGNORECASE) for regex in config['channel_ignore']['regex']]
programme_include = [re.compile(regex, re.IGNORECASE) for regex in config['programmes']['regex']]
programme_ignore = [re.compile(regex, re.IGNORECASE) for regex in config['programme_ignore']['regex']]
synopsis_ignore = [re.compile(regex, re.IGNORECASE) for regex in config['synopsis_ignore']['regex']]

channel_specifics = []
for channel_specific in config['channel_specific']:
    channel_specifics.append(
    { 
        'channel_regex': [re.compile(regex, re.IGNORECASE) for regex in channel_specific['channels']['regex']],
        'prog_regex': [re.compile(regex, re.IGNORECASE) for regex in channel_specific['programmes']['regex']],
    })

series_ignores = []
for series_ignore in config['series_ignore']:
    for prog_regex, series_array in series_ignore.items():
        series_ignores.append(
        {
            'prog_regex': re.compile(prog_regex, re.IGNORECASE),
            'series_numbers': series_array
        })


def get_day(start_time):
    req = requests.get('https://www.freeview.co.uk/api/tv-guide', params={
        'nid': region_id,
        'start': int(start_time.timestamp())
    })

    if not req.ok:
        print(req.status_code, req.reason)
        print(req.text)
        exit(1)

    guide = req.json()

    # Example response:
    """
    {
        "status": "success",
        "data": {
            "programs": [
                {
                    "service_id": "4672",
                    "title": "CBeebies",
                    "events": [
                        {
                            "program_id": "crid://bbc.co.uk/nitro/episode/b063cph3",
                            "event_locator": "dvb://233a..1240;56b8",
                            "main_title": "Peter Rabbit",
                            "secondary_title": "Series 2: 16. The Tale of the Lost Journal",
                            "image_url": "https://img.freeviewplay.tv/p524c7623eb739804a42fb6a9d3a90db9",
                            "start_time": "2021-03-27T08:00:00+0000",
                            "duration": "PT10M",
                            "on_demand": {
                                "start_of_availability": "2021-03-27T08:10:00+0000",
                                "end_of_availability": "2021-04-26T08:10:00+0000",
                                "player_links": {
                                    "tv": {
                                        "program_url": "https://www.live.bbctvapps.co.uk/tap/iplayer/ait/launch/iplayer.aitx?deeplink=tv/playback/b063cph3",
                                        "template_url": "https://www.live.bbctvapps.co.uk/tap/iplayer/ait/launch/iplayer.aitx"
                                    }
                                }
                            },
                            "genre": "urn:fvc:metadata:cs:ContentSubjectCS:2014-07:5",
                            "uuid": "14c2a49f9b151e520b842d1424be4660"
                        },
    """

    def matches_any(regexes, text):
        for regex in regexes:
            if regex.search(text):
                return True
        return False

    pr_progs = []
    for channel in guide['data']['programs']:
        channel_name = channel['title']
        if matches_any(channel_ignore, channel_name):
            continue
        for event in channel['events']:
            title = re.sub(r'\s+', ' ', event['main_title'])

            channel_specific_match = False
            for channel_specific in channel_specifics:
                channel_specific_match |= matches_any(channel_specific['channel_regex'], channel_name) and \
                    matches_any(channel_specific['prog_regex'], title)

            if (channel_specific_match or matches_any(programme_include, title)) and \
                    not matches_any(programme_ignore, title):

                event['channel'] = channel_name
                start_time = datetime.strptime(event['start_time'], '%Y-%m-%dT%H:%M:%S%z')
                filtered_event = {
                    x: event[x] for x in ['main_title', 'secondary_title', 'start_time', 'channel'] if x in event.keys()
                }
                filtered_event['start'] = start_time.astimezone(tz).strftime('%a %d %b %H:%M %Z')
                filtered_event['start_hhmm'] = start_time.astimezone(tz).strftime('%H:%M')

                if 'secondary_title' in filtered_event:
                    match = season_episode_regex.search(filtered_event['secondary_title'])
                    if match:
                        filtered_event['series_number'] = int(match.group(1))
                        filtered_event['episode_number'] = int(match.group(3))

                # Get extra details, if possible
                req = requests.get('https://www.freeview.co.uk/api/program', params={
                    'pid': event['program_id']
                })
                synopsis = None
                if req.ok and len(req.json()['data']['programs']) > 0:
                    extra_info = req.json()['data']['programs'][0]
                    if isinstance(extra_info['synopsis'], dict):
                        synopsi = extra_info['synopsis'].keys()
                        if 'short' in synopsi:
                            synopsis = extra_info['synopsis']['short']
                        elif 'medium' in synopsi:
                            synopsis = extra_info['synopsis']['medium']
                        elif 'long' in synopsi:
                            synopsis = extra_info['synopsis']['long']
    
                if synopsis:
                    filtered_event['synopsis'] = synopsis
                    match = season_episode_regex.search(synopsis)
                    if match:
                        filtered_event['synopsis_season'] = match.group(0)
                        filtered_event['series_number'] = int(match.group(1))
                        filtered_event['episode_number'] = int(match.group(3))

                    if title.endswith('...') and synopsis.startswith('...'):
                        # Example title: "George Clarke's Build a New..."
                        # Example synopsis start: "...Life in the Country. Property series ..."
                        title_continuation, actual_synopsis = re.split(r'[.?!:]', synopsis[3:], maxsplit=1)
                        # Some programmes have two-part titles, e.g. Kirstie and Phil's Love It or List It: Brilliant Builds
                        lioli_bb = ' Brilliant Builds'
                        if actual_synopsis.startswith(lioli_bb):
                            title_continuation += ':' + actual_synopsis[0: len(lioli_bb)]
                            actual_synopsis = actual_synopsis[len(lioli_bb):]
                            
                        title = title[0:-3] + ' ' + title_continuation
                        synopsis = actual_synopsis.lstrip(' .:?!')
                        filtered_event['main_title'] = title
                    
                    episode_match = episode_title_regex.search(synopsis)
                    if episode_match:
                        possible_episode_title = episode_match.group(0)
                        if not_episode_title_regex.search(possible_episode_title):
                            pass
                        elif 'synopsis_season' not in filtered_event.keys():
                            filtered_event['synopsis_season'] = possible_episode_title
                        else:
                            filtered_event['synopsis_season'] += ': ' + possible_episode_title
                
                ignore = False
                if 'series_number' in filtered_event:
                    for series_ignore in series_ignores:
                        if series_ignore['prog_regex'].match(filtered_event['main_title']):
                            ignore |= filtered_event['series_number'] in series_ignore['series_numbers']
                
                if 'synopsis' in filtered_event:
                    ignore |= matches_any(synopsis_ignore, filtered_event['synopsis'])

                if not ignore:
                    pr_progs.append(filtered_event)
    return pr_progs

progs = []
progs_by_day = OrderedDict()
if range_days:
    for delta_days in range(range_days):
        start_time = start_time = today + timedelta(days=delta_days)
        progs_of_day = get_day(start_time)
        progs.extend(progs_of_day)
        progs_by_day[start_time.astimezone(tz).strftime('%a %d %b')] = progs_of_day
else:
    start_time = start_time = today + timedelta(days=delta_days)
    progs = get_day(start_time)
    progs_by_day[start_time.astimezone(tz).strftime('%a %d %b')] = progs

col_widths = {}
if len(progs) > 0:
    for prog in progs:
        col_widths.update({ col: 0 for col in prog.keys() })
for prog in progs:
    for col in [key for key in prog.keys() if key not in ['series_number', 'episode_number']]:
        col_widths[col] = max(col_widths[col], len(prog[col]))

if not named_args.html:
    for prog in progs:
        for col, width in col_widths.items():
            if col in ['start_time']:
                continue
            value = ''
            if col in prog.keys():
                value = prog[col]
            # print(f"{value:{width}}  ", end='')
            format = '%-' + str(width) + 's  '
            print(format % value, end='')
        print()

else:
    print('<html>')
    print('Updated', datetime.now().strftime('%a %d %b %H:%M %Z'))
    print('<table>')
    for day, progs_of_day in reversed(progs_by_day.items()):
        print('<tr><td><br><b>' + str(day) + '</b></td></tr>')

        for prog in progs_of_day:
            print('<tr>', end='')
            print('<td>' + prog['main_title'], end='')
            if 'secondary_title' in prog.keys():
                print('<br>&nbsp;&nbsp;&angrt;&nbsp;' + prog['secondary_title'], end='')
            elif 'synopsis_season' in prog.keys():
                print('<br>&nbsp;&nbsp;&angrt;&nbsp;' + prog['synopsis_season'], end='')
            print('</td>', end='')
            for col in ['start_hhmm', 'channel']:
                value = prog[col]
                print('<td>' + value + '</td>', end='')
            print('</tr>')

    print('</table></html>')
