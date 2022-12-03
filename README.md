# Rainbow CSV
![rainbow_csv](https://i.imgur.com/EhV2niB.png)

### Main features

* Highlight columns in *.csv, *.tsv and other separated files in different rainbow colors.
* Provide info about columns on mouse hover.
* Check consistency of CSV files (CSVLint)
* Align columns with spaces and Shrink (trim spaces from fields)
* Execute SQL-like RBQL queries.

![screenshot](https://i.imgur.com/UtGKbEg.png)

### Usage
Rainbow CSV has content-based csv/tsv autodetection mechanism. This means that the package will analyze plain text files even if they do not have "*.csv" or "*.tsv" extension.  

Rainbow highlighting can also be manually enabled from Sublime context menu (see the demo gif below):  
1. Select a character (or sequence of characters) that you want to use as a delimiter with the cursor
2. Right mouse click: context menu -> Rainbow CSV -> Enable ...  

You can also disable rainbow highlighting and go back to the original file highlighting using the same context menu.  
This feature can be used to temporarily rainbow-highlight even non-table files.  

Manual Rainbow Enabling/Disabling demo gif:  
![demo](https://i.imgur.com/7lSSMst.gif)

Rainbow CSV also lets you execute SQL-like queries in RBQL language, see the demo gif below:  
![demo gif](https://i.imgur.com/UF6zM4i.gif)

To Run RBQL query press **F5** or select "Rainbow CSV" -> "Run RBQL query" option from the file context menu.  


### Key mappings

|Key                       | Action                                             |
|--------------------------|----------------------------------------------------|
|**F5**                    | Start query editing for the current CSV file       |

### Commands

#### Rainbow CSV: Enable Simple
Before running the command you need to select the separator (single or multiple characters) with your cursor
Set the selected character as the separator and enables syntax highlighting. Sublime will generate the syntax file if it doesn't exist.
Simple dialect completely ignores double quotes: i.e. separators can not be escaped in double quoted fields

#### Rainbow CSV: Enable Standard
Same as the _Enable Simple_ command, but separators can be escaped in double quoted fields.

#### Rainbow CSV: CSVLint
The linter checks the following:  
* consistency of double quotes usage in CSV rows  
* consistency of number of fields per CSV row  

#### Rainbow CSV: Run RBQL query
Run RBQL query for the current file.  
Unlike F5 button it will work even if the current file is not a CSV table: in this case only 2 variables "a1" and "NR" will be available.

#### Rainbow CSV: Align CSV columns with spaces
Align CSV columns with spaces in the current file

#### Rainbow CSV: Shrink CSV table
Remove leading and trailing spaces from all fields in the current file


### Configuration

To adjust plugin configuration:  
1. Go to "Preferences" -> "Package Settings" -> "Rainbow CSV" -> "Settings".  
2. On the right side change the settings like you'd like.  


### Configuration parameters

To configure the extension, click "Preferences" -> "Package Settings" -> "Rainbow CSV" -> "Settings"

#### "allow_newlines_in_fields"
Allow quoted multiline fields as defined in [RFC-4180](https://tools.ietf.org/html/rfc4180)

#### "enable_rainbow_csv_autodetect"
Enable content-based separator autodetection. 
Files with ".csv" and ".tsv" extensions are always highlighted no matter what is the value of this option.

#### "rainbow_csv_autodetect_dialects"
List of CSV dialects to autodetect.  
If "enable_rainbow_csv_autodetect" is set to false this setting is ignored  

#### "rainbow_csv_max_file_size_bytes"
Disable Rainbow CSV for files bigger than the specified size. This can be helpful to prevent poor performance and crashes with very large files.  
Manual separator selection will override this setting for the current file.  
E.g. to disable on files larger than 100 MB, set `"rainbow_csv_max_file_size_bytes": 100000000`  

#### "use_custom_rainbow_colors"
Use custom high-contrast rainbow colors instead of colors provided by your current color scheme. 
When you enable this option, "auto_adjust_rainbow_colors" also gets enabled by default.

#### "auto_adjust_rainbow_colors"
Auto adjust rainbow colors for Packages/User/RainbowCSV.sublime-color-scheme  
Rainbow CSV will auto-generate color theme with high-contrast colors to make CSV columns more distinguishable.  
You can disable this setting and manually customize Rainbow CSV color scheme at `Packages/User/RainbowCSV.sublime-color-scheme`, you can use the following [RainbowCSV.sublime-color-scheme](https://github.com/mechatroner/sublime_rainbow_csv/blob/master/RainbowCSV.sublime-color-scheme) file as a starting point for your customizations. 
Do NOT manually customize Packages/User/RainbowCSV.sublime-color-scheme without disabling this setting, the plugin will just rewrite it in that case.
This option has effect only if "use_custom_rainbow_colors" is set to true

#### "rbql_backend_language"
RBQL backend language.  
Supported values: _"Python"_, _"JS"_  
To use RBQL with JavaScript (JS) you need to have Node JS installed and added to your system path.  

#### "rbql_with_headers"
Default: false
RBQL will treat first records in all input and join files as headers.  
You can set this value to true if most of the CSV files you deal with have headers.  
You can override this setting on the query level by either adding `WITH (header)` or `WITH (noheader)` to the end of the query.  

#### "rbql_output_format"
Format of RBQL result set tables.  
Supported values: _"tsv"_, _"csv"_, _"input"_  
* input: same format as the input table
* tsv: tab separated values.
* csv: is Excel-compatible and allows quoted commas.

Example: to always use "tsv" as output format add this line to your settings file: `"rbql_output_format": "tsv",`

#### "rbql_encoding"
RBQL encoding for files and queries.  
Supported values: _"latin-1"_, _"utf-8"_  


### References

* This Sublime Text plugin is an adaptation of Vim's rainbow_csv [plugin](https://github.com/mechatroner/rainbow_csv)


# RBQL (Rainbow Query Language) Description

RBQL is an eval-based SQL-like query engine for (not only) CSV file processing. It provides SQL-like language that supports SELECT queries with Python or JavaScript expressions.  
RBQL is best suited for data transformation, data cleaning, and analytical queries.  
RBQL is distributed with CLI apps, text editor plugins, Python and JS libraries.  

[Official Site](https://rbql.org/)

### Main Features

* Use Python or JavaScript expressions inside _SELECT_, _UPDATE_, _WHERE_ and _ORDER BY_ statements
* Supports multiple input formats
* Result set of any query immediately becomes a first-class table on its own
* No need to provide FROM statement in the query when the input table is defined by the current context.
* Supports all main SQL keywords
* Supports aggregate functions and GROUP BY queries
* Supports user-defined functions (UDF)
* Provides some new useful query modes which traditional SQL engines do not have
* Lightweight, dependency-free, works out of the box

#### Limitations:

* RBQL doesn't support nested queries, but they can be emulated with consecutive queries
* Number of tables in all JOIN queries is always 2 (input table and join table), use consecutive queries to join 3 or more tables

### Supported SQL Keywords (Keywords are case insensitive)

* SELECT
* UPDATE
* WHERE
* ORDER BY ... [ DESC | ASC ]
* [ LEFT | INNER ] JOIN
* DISTINCT
* GROUP BY
* TOP _N_
* LIMIT _N_
* AS

All keywords have the same meaning as in SQL queries. You can check them [online](https://www.w3schools.com/sql/default.asp)  


### RBQL variables
RBQL for CSV files provides the following variables which you can use in your queries:

* _a1_, _a2_,..., _a{N}_  
   Variable type: **string**  
   Description: value of i-th field in the current record in input table  
* _b1_, _b2_,..., _b{N}_  
   Variable type: **string**  
   Description: value of i-th field in the current record in join table B  
* _NR_  
   Variable type: **integer**  
   Description: Record number (1-based)  
* _NF_  
   Variable type: **integer**  
   Description: Number of fields in the current record  
* _a.name_, _b.Person_age_, ... _a.{Good_alphanumeric_column_name}_  
   Variable type: **string**  
   Description: Value of the field referenced by it's "name". You can use this notation if the field in the header has a "good" alphanumeric name  
* _a["object id"]_, _a['9.12341234']_, _b["%$ !! 10 20"]_ ... _a["Arbitrary column name!"]_  
   Variable type: **string**  
   Description: Value of the field referenced by it's "name". You can use this notation to reference fields by arbitrary values in the header


### UPDATE statement

_UPDATE_ query produces a new table where original values are replaced according to the UPDATE expression, so it can also be considered a special type of SELECT query.

### Aggregate functions and queries

RBQL supports the following aggregate functions, which can also be used with _GROUP BY_ keyword:  
_COUNT_, _ARRAY_AGG_, _MIN_, _MAX_, _SUM_, _AVG_, _VARIANCE_, _MEDIAN_  

Limitation: aggregate functions inside Python (or JS) expressions are not supported. Although you can use expressions inside aggregate functions.  
E.g. `MAX(float(a1) / 1000)` - valid; `MAX(a1) / 1000` - invalid.  
There is a workaround for the limitation above for _ARRAY_AGG_ function which supports an optional parameter - a callback function that can do something with the aggregated array. Example:  
`SELECT a2, ARRAY_AGG(a1, lambda v: sorted(v)[:5]) GROUP BY a2` - Python; `SELECT a2, ARRAY_AGG(a1, v => v.sort().slice(0, 5)) GROUP BY a2` - JS


### JOIN statements

Join table B can be referenced either by its file path or by its name - an arbitrary string which the user should provide before executing the JOIN query.  
RBQL supports _STRICT LEFT JOIN_ which is like _LEFT JOIN_, but generates an error if any key in the left table "A" doesn't have exactly one matching key in the right table "B".  
Table B path can be either relative to the working dir, relative to the main table or absolute.  
Limitation: _JOIN_ statements can't contain Python/JS expressions and must have the following form: _<JOIN\_KEYWORD> (/path/to/table.tsv | table_name ) ON a... == b... [AND a... == b... [AND ... ]]_

### SELECT EXCEPT statement

SELECT EXCEPT can be used to select everything except specific columns. E.g. to select everything but columns 2 and 4, run: `SELECT * EXCEPT a2, a4`  
Traditional SQL engines do not support this query mode.


### UNNEST() operator
UNNEST(list) takes a list/array as an argument and repeats the output record multiple times - one time for each value from the list argument.  
Example: `SELECT a1, UNNEST(a2.split(';'))`  


### LIKE() function
RBQL does not support LIKE operator, instead it provides "like()" function which can be used like this:
`SELECT * where like(a1, 'foo%bar')`


### WITH (header) and WITH (noheader) statements
You can set whether the input (and join) CSV file has a header or not using the environment configuration parameters which could be `--with_headers` CLI flag or GUI checkbox or something else.
But it is also possible to override this selection directly in the query by adding either `WITH (header)` or `WITH (noheader)` statement at the end of the query.
Example: `select top 5 NR, * with (header)`


### User Defined Functions (UDF)

RBQL supports User Defined Functions  
You can define custom functions and/or import libraries in two special files:  
* `~/.rbql_init_source.py` - for Python
* `~/.rbql_init_source.js` - for JavaScript


## Examples of RBQL queries

#### With Python expressions

* `SELECT TOP 100 a1, int(a2) * 10, len(a4) WHERE a1 == "Buy" ORDER BY int(a2) DESC`
* `SELECT a.id, a.weight / 1000 AS weight_kg`
* `SELECT * ORDER BY random.random()` - random sort
* `SELECT len(a.vehicle_price) / 10, a2 WHERE int(a.vehicle_price) < 500 and a['Vehicle type'] in ["car", "plane", "boat"] limit 20` - referencing columns by names from header and using Python's "in" to emulate SQL's "in"
* `UPDATE SET a3 = 'NPC' WHERE a3.find('Non-playable character') != -1`
* `SELECT NR, *` - enumerate records, NR is 1-based
* `SELECT * WHERE re.match(".*ab.*", a1) is not None` - select entries where first column has "ab" pattern
* `SELECT a1, b1, b2 INNER JOIN ./countries.txt ON a2 == b1 ORDER BY a1, a3` - example of join query
* `SELECT MAX(a1), MIN(a1) WHERE a.Name != 'John' GROUP BY a2, a3` - example of aggregate query
* `SELECT *a1.split(':')` - Using Python3 unpack operator to split one column into many. Do not try this with other SQL engines!

#### With JavaScript expressions

* `SELECT TOP 100 a1, a2 * 10, a4.length WHERE a1 == "Buy" ORDER BY parseInt(a2) DESC`
* `SELECT a.id, a.weight / 1000 AS weight_kg`
* `SELECT * ORDER BY Math.random()` - random sort
* `SELECT TOP 20 a.vehicle_price.length / 10, a2 WHERE parseInt(a.vehicle_price) < 500 && ["car", "plane", "boat"].indexOf(a['Vehicle type']) > -1 limit 20` - referencing columns by names from header
* `UPDATE SET a3 = 'NPC' WHERE a3.indexOf('Non-playable character') != -1`
* `SELECT NR, *` - enumerate records, NR is 1-based
* `SELECT a1, b1, b2 INNER JOIN ./countries.txt ON a2 == b1 ORDER BY a1, a3` - example of join query
* `SELECT MAX(a1), MIN(a1) WHERE a.Name != 'John' GROUP BY a2, a3` - example of aggregate query
* `SELECT ...a1.split(':')` - Using JS "destructuring assignment" syntax to split one column into many. Do not try this with other SQL engines!


### References

#### Rainbow CSV and similar plugins in other editors:

* Rainbow CSV extension in [Vim](https://github.com/mechatroner/rainbow_csv)
* Rainbow CSV extension in [Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=mechatroner.rainbow-csv)
* rainbow-csv package in [Atom](https://atom.io/packages/rainbow-csv)
* rainbow_csv plugin in [gedit](https://github.com/mechatroner/gtk_gedit_rainbow_csv) - doesn't support quoted commas in csv
* rainbow_csv_4_nedit in [NEdit](https://github.com/DmitTrix/rainbow_csv_4_nedit)
* CSV highlighting in [Nano](https://github.com/scopatz/nanorc)
* Rainbow CSV in [IntelliJ IDEA](https://plugins.jetbrains.com/plugin/12896-rainbow-csv/)

#### RBQL:

* [RBQL: Official Site](https://rbql.org/)
* RBQL is integrated with Rainbow CSV extensions in [Vim](https://github.com/mechatroner/rainbow_csv), [VSCode](https://marketplace.visualstudio.com/items?itemName=mechatroner.rainbow-csv), [Sublime Text](https://packagecontrol.io/packages/rainbow_csv) and [Atom](https://atom.io/packages/rainbow-csv) editors.
* [RBQL in npm](https://www.npmjs.com/package/rbql): `$ npm install -g rbql`
* [RBQL in PyPI](https://pypi.org/project/rbql/): `$ pip install rbql`

