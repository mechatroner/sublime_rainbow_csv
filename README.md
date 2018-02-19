# Rainbow CSV

### Main features

* Highlight columns in *.csv, *.tsv and other separated files in different rainbow colors.
* Provide info about columns on mouse hover.

![screenshot](https://i.imgur.com/UtGKbEg.png)

### Usage
rainbow_csv has content-based csv/tsv autodetection mechanism. This means that package will analyze plain text files even if they do not have "*.csv" or "*.tsv" extension.

Rainbow highlighting can also be manually enabled from Sublime context menu:
1. Select a character that you want to use as a delimiter with mouse. Delimiter can be any non-alphanumeric printable ASCII symbol, e.g. semicolon
2. Right mouse click: context menu -> Rainbow CSV -> Enable ...

You can also disable rainbow highlighting and go back to the original file highlighting using the same context menu.
This feature can be used to temporary rainbow-highlight even non-table files.

#### Difference between "Standard" and "Simple" dialects
When manually enabling rainbow highlighting from the context menu, you have to choose between "Standard" and "Simple" dialect.
* __Standard dialect__ will treat quoted separator as a single field. E.g. line `sell,"15,128",23%` will be treated as 3 columns, because the second comma is quoted. This dialect is used by Excel.
* __Simple dialect__ doesn't care about double quotes: the number of highlighted fields is always N + 1 where N is the number of separators.



### References

* This Sublime Text plugin is an adaptation of Vim's rainbow_csv [plugin](https://github.com/mechatroner/rainbow_csv)
