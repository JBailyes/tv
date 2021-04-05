#!/bin/env python3.9

import argparse
import requests
import json
import re

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

arg_parser = argparse.ArgumentParser()
named_args, pos_args = arg_parser.parse_known_args()

london = ZoneInfo('Europe/London')

today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
command = ' '.join(pos_args).lower()

delta_days = 0
weekdays = [re.compile(regex) for regex in [
    r'mon', r'tue', r'wed', r'thu', r'fri', r'sat', r'sun'
]]

next_7 = []
for day_number in range(today.weekday() + 1, today.weekday() + 8):
    next_7.append(weekdays[day_number % 7])

if 'tomorrow' in command:
    delta_days = 1
elif 'yesterday' in command:
    delta_days = -1
else:
    for index, weekday in enumerate(next_7):
        if weekday.search(command):
            delta_days = index + 1
            break

start_time = start_time = today + timedelta(days=delta_days)


region_id = 64320
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

channel_ignore = [re.compile(regex, re.IGNORECASE) for regex in [
    r' HD$',
    r'\+1$',
    r'Radio',
    r'BBC [56]',
]]
programme_words = [re.compile(regex, re.IGNORECASE) for regex in [
    r'Peter Rabbit',
    r'Noddy Toyload',
    r'Postman Pat',
    r'Engineering',
    r'\bRail(\b|way)',
    r'Trains?\b',
    r'Grand Designs',
    r'Selling Houses Australia',
    r'Formula ?(One|1)|F1',
    r'^New\b',
]]
programme_ignore = [re.compile(regex, re.IGNORECASE) for regex in [
    r'Great (British|Continental) Railway Journeys',
    r'Scenic Railway|Night Train To Lisbon',
    r'The Railway: First Great Western',
    r'Abandoned Engineering|Disasters Engineered|Engineering Disasters',
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
        title = event['main_title']
        if matches_any(programme_words, title) and not matches_any(programme_ignore, title):
            event['channel'] = channel_name
            start_time = datetime.strptime(event['start_time'], '%Y-%m-%dT%H:%M:%S%z')
            filtered_event = {
                x: event[x] for x in ['main_title', 'secondary_title', 'start_time', 'channel'] if x in event.keys()
            }
            filtered_event['start'] = start_time.astimezone(london).strftime('%a %d %b %H:%M %Z')
            pr_progs.append(filtered_event)
print(json.dumps(pr_progs, indent=4))

# Fetching a programme's details
# https://www.freeview.co.uk/api/program?sid=4161&nid=64320&pid=crid://bbc.co.uk/nitro/episode/m000tjk1&start_time=2021-03-26T15%3A45%3A00%2B0000&duration=PT45M