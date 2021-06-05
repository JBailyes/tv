Scan the Freeview TV guide, filter the results to those that are likely to be of interest

# Config file

Config file data format is YAML

`timezone_name`: IANA/Olson database name for the timezone to use

`freeview_region_id`: Region ID of the Freeview region of interest

The config file has sections for text (not implemented yet) or regular expressions for filtering programmes of interest

- `channel_ignore`: Ingore results from channels whose names are matched by at least one of the text lines or regular expressions
- `programmes`: Key text or regular expressions that are of interest in programme names
- `programme_ignore`: Filter-out results that match the text or regular expressions, even if they matched in `programmes`
- `channel_specific`: Patterns for channel names and programme names can be associated, such that the programmes are only matched if they appear on a matching channgel

Config file contents example:

```yaml
timezone_region: 'Europe/London'
freeview_region_id: 64320

channel_ignore:
    regex:
    - ' HD$'
    - '\+1$'
    - 'Radio'

programmes:
    regex:
    - 'Builds?\b'

programme_ignore:
    regex:
    - 'Cowboy Builders'

channel_specific:
    - channels:
        regex:
        - '^BBC'
      programmes:
        regex:
        - 'Bake'  
```