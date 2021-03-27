#!/bin/env python3

import argparse
import requests
import json
import re

from datetime import datetime, timedelta

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('---tomorrow', action='store_true')
args = arg_parser.parse_args()

today = datetime.now().replace(hour=0, minute=0, second=0)

start_time = today
if args.tomorrow:
    start_time = today + timedelta(days=1)


region_id = 64320
start_timestamp = 1616803200
req = requests.get('https://www.freeview.co.uk/api/tv-guide', params={
    'nid': region_id,
    'start': int(start_time.timestamp())
})

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

channel_ignore = [re.compile(regex) for regex in [
    r' HD$',
    r'\+1$',
]]
programme_words = [re.compile(regex) for regex in [
    r'Peter Rabbit',
    r'Noddy Toyload',
    r'Postman Pat',
    r'Engineering',
    r'Railway',
    r'Trains?\b',
    r'Grand Designs',
    r'Selling Houses Australia',
]]

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
        if matches_any(programme_words, event['main_title']):
            event['channel'] = channel_name
            pr_progs.append({
                x: event[x] for x in ['main_title', 'secondary_title', 'start_time', 'channel'] if x in event.keys()
            })
print(json.dumps(pr_progs, indent=4))

# Fetching a programme's details
# https://www.freeview.co.uk/api/program?sid=4161&nid=64320&pid=crid://bbc.co.uk/nitro/episode/m000tjk1&start_time=2021-03-26T15%3A45%3A00%2B0000&duration=PT45M