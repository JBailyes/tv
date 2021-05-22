Scan the Freeview TV guide, filter the results to those that are likely to be of interest

The config file has sections for words or regular expressions

- channel_ignore: Ingore results from channels whose names are matched by at least one of the words or regular expressions
- programme_words: Key words or regular expressions that are of interest in programme names
- programme_ignore: Filter-out results that match the words or regular expressions, even if they matched in programme_words

Config file data format is YAML
Config file contents example:

```yaml
channel_ignore:
    regex:
    - ' HD$'
    - '\+1$'
    - 'Radio'

programmes:
    regex:
    - 'Builds?'

programme_ignore:
    regex:
    - 'Cowboy Builders'
```