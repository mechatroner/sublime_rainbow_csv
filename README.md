![logo](https://i.imgur.com/cJwEvyM.png)

# Rainbow CSV

### Main features

* Highlight columns in *.csv, *.tsv and other separated files in different rainbow colors.
* Provide info about columns on mouse hover.
* Check consistency of CSV files (CSVLint)
* Execute SQL-like RBQL queries.

![screenshot](https://i.imgur.com/UtGKbEg.png)

### Usage
Rainbow CSV has content-based csv/tsv autodetection mechanism. This means that package will analyze plain text files even if they do not have "*.csv" or "*.tsv" extension.  

Rainbow highlighting can also be manually enabled from Sublime context menu (see the demo gif below):  
1. Select a character that you want to use as a delimiter with mouse. Delimiter can be any non-alphanumeric printable ASCII symbol, e.g. semicolon  
2. Right mouse click: context menu -> Rainbow CSV -> Enable ...  

You can also disable rainbow highlighting and go back to the original file highlighting using the same context menu.  
This feature can be used to temporary rainbow-highlight even non-table files.  

Manual Rainbow Enabling/Disabling demo gif:  
![demo](https://i.imgur.com/7lSSMst.gif)

Rainbow CSV also lets you execute SQL-like queries in RBQL language, see the demo gif below:  
![demo gif](https://i.imgur.com/UF6zM4i.gif)

To Run RBQL query press **F5** or select "Rainbow CSV" -> "Run RBQL query" option from the file context menu.  

#### Difference between "Standard" and "Simple" dialects
When manually enabling rainbow highlighting from the context menu, you have to choose between "Standard" and "Simple" dialect.  
* __Standard dialect__ will treat quoted separator as a single field. E.g. line `sell,"15,128",23%` will be treated as 3 columns, because the second comma is quoted. This dialect is used by Excel.  
* __Simple dialect__ doesn't care about double quotes: the number of highlighted fields is always N + 1 where N is the number of separators.  

### Key mappings

|Key                       | Action                                             |
|--------------------------|----------------------------------------------------|
|**F5**                    | Start query editing for the current csv file       |


### Configuration

To adjust plugin configuration:  
1. Go to "Preferences" -> "Package Settings" -> "Rainbow CSV" -> "Settings".  
2. On the right side change the settings like you'd like.  


### Configuration parameters

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

#### "auto_adjust_rainbow_colors"
Auto adjust rainbow colors for Packages/User/RainbowCSV.sublime-color-scheme  
Rainbow CSV will auto-generate color theme with high-contrast colors to make CSV columns more distinguishable.  
You can disable this setting and manually customize Rainbow CSV color scheme at Packages/User/RainbowCSV.sublime-color-scheme  
Do not customize Packages/User/RainbowCSV.sublime-color-scheme without disabling the setting, it will be rewritten by the plugin  

#### "rbql_backend_language"
RBQL backend language.  
Supported values: _"Python"_, _"JS"_  
In order to use RBQL with JavaScript (JS) you need to have Node JS installed and added to your system path.  

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

RBQL is a technology which provides SQL-like language that supports _SELECT_ and _UPDATE_ queries with Python or JavaScript expressions.  
RBQL is distributed with CLI apps, text editor plugins, Python and JS libraries and can work in web browsers.  
RBQL core module is very generic and can process all kind of objects and record formats, but most popular RBQL implementation works with CSV files.  

[Official Site](https://rbql.org/)

### Main Features

* Use Python or JavaScript expressions inside _SELECT_, _UPDATE_, _WHERE_ and _ORDER BY_ statements
* Result set of any query immediately becomes a first-class table on it's own
* Supports input tables with inconsistent number of fields per record
* Output records appear in the same order as in input unless _ORDER BY_ is provided
* Each record has a unique NR (record number) identifier
* Supports all main SQL keywords
* Supports aggregate functions and GROUP BY queries
* Provides some new useful query modes which traditional SQL engines do not have
* Supports both _TOP_ and _LIMIT_ keywords
* Supports user-defined functions (UDF)
* Works out of the box, no external dependencies

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
* _a.name_, _b.Person_age_, ... _a.{good_alphanumeric_column_name}_  
   Variable type: **string**  
   Description: Value of the field referenced by it's "name". You can use this notation if the field in the first (header) CSV line has a "good" alphanumeric name  
* _a["object id"]_, _a['9.12341234']_, _b["%$ !! 10 20"]_ ... _a["arbitrary column name!"]_  
   Variable type: **string**  
   Description: Value of the field referenced by it's "name". You can use this notation to reference fields by arbitrary values in the first (header) CSV line, even when there is no header at all  


#### Notes:
* You can mix all variable types in a single query, example:
  ```select a1, b2 JOIN /path/to/b.csv ON a['Item Id'] == b.Identifier WHERE NR > 1 and int(a.Weight) * 100 > int(b["weight of the item"])```
* Referencing fields by header names does not automatically skip the header line (you can use `where NR > 1` trick to skip it)
* If you want to use RBQL as a library for your own app you can define your own custom variables and do not have to support the above mentioned CSV-related variables.


### UPDATE statement

_UPDATE_ query produces a new table where original values are replaced according to the UPDATE expression, so it can also be considered a special type of SELECT query. This prevents accidental data loss from poorly written queries.  
_UPDATE SET_ is synonym to _UPDATE_, because in RBQL there is no need to specify the source table.  


### Aggregate functions and queries

RBQL supports the following aggregate functions, which can also be used with _GROUP BY_ keyword:  
_COUNT_, _ARRAY_AGG_, _MIN_, _MAX_, _SUM_, _AVG_, _VARIANCE_, _MEDIAN_  

Limitation: aggregate functions inside Python (or JS) expressions are not supported. Although you can use expressions inside aggregate functions.  
E.g. `MAX(float(a1) / 1000)` - valid; `MAX(a1) / 1000` - invalid.  
There is a workaround for the limitation above for _ARRAY_AGG_ function which supports an optional parameter - a callback function that can do something with the aggregated array. Example:  
`select a2, ARRAY_AGG(a1, lambda v: sorted(v)[:5]) group by a2` - Python; `select a2, ARRAY_AGG(a1, v => v.sort().slice(0, 5)) group by a2` - JS


### JOIN statements

Join table B can be referenced either by it's file path or by it's name - an arbitary string which user should provide before executing the JOIN query.  
RBQL supports _STRICT LEFT JOIN_ which is like _LEFT JOIN_, but generates an error if any key in left table "A" doesn't have exactly one matching key in the right table "B".  
Limitation: _JOIN_ statements must have the following form: _<JOIN\_KEYWORD> (/path/to/table.tsv | table_name ) ON ai == bj_  


### SELECT EXCEPT statement

SELECT EXCEPT can be used to select everything except specific columns. E.g. to select everything but columns 2 and 4, run: `SELECT * EXCEPT a2, a4`  
Traditional SQL engines do not support this query mode.


### UNNEST() operator
UNNEST(list) takes a list/array as an argument and repeats the output record multiple times - one time for each value from the list argument.  
Example: `SELECT a1, UNNEST(a2.split(';'))`  


### User Defined Functions (UDF)

RBQL supports User Defined Functions  
You can define custom functions and/or import libraries in two special files:  
* `~/.rbql_init_source.py` - for Python
* `~/.rbql_init_source.js` - for JavaScript


## Examples of RBQL queries

#### With Python expressions

* `select top 100 a1, int(a2) * 10, len(a4) where a1 == "Buy" order by int(a2) desc`
* `select * order by random.random() where NR > 1` - skip header record and random sort
* `select len(a.vehicle_price) / 10, a2 where NR > 1 and a['Vehicle type'] in ["car", "plane", "boat"] limit 20` - referencing columns by names from header record, skipping the header and using Python's "in" to emulate SQL's "in"
* `update set a3 = 'NPC' where a3.find('Non-playable character') != -1`
* `select NR, *` - enumerate records, NR is 1-based
* `select * where re.match(".*ab.*", a1) is not None` - select entries where first column has "ab" pattern
* `select a1, b1, b2 inner join ./countries.txt on a2 == b1 order by a1, a3` - example of join query
* `select MAX(a1), MIN(a1) where a.Name != 'John' group by a2, a3` - example of aggregate query

#### With JavaScript expressions

* `select top 100 a1, a2 * 10, a4.length where a1 == "Buy" order by parseInt(a2) desc`
* `select * order by Math.random() where NR > 1` - skip header record and random sort
* `select top 20 a.vehicle_price.length / 10, a2 where NR > 1 and ["car", "plane", "boat"].indexOf(a['Vehicle type']) > -1 limit 20` - referencing columns by names from header record and skipping the header
* `update set a3 = 'NPC' where a3.indexOf('Non-playable character') != -1`
* `select NR, *` - enumerate records, NR is 1-based
* `select a1, b1, b2 inner join ./countries.txt on a2 == b1 order by a1, a3` - example of join query
* `select MAX(a1), MIN(a1) where a.Name != 'John' group by a2, a3` - example of aggregate query


### FAQ

#### How do I skip header record in CSV files?

You can use the following trick: add `... where NR > 1 ...` to your query  

And if you are doing math operation you can modify your query like this, example:  
`select int(a3) * 1000, a2` -> `select int(a3) * 1000 if NR > 1 else a3, a2`  


#### How does RBQL work?

RBQL parses SQL-like user query, creates a new python or javascript worker module, then imports and executes it.  

Explanation of simplified Python version of RBQL algorithm by example.
1. User enters the following query, which is stored as a string _Q_:
```
    SELECT a3, int(a4) + 100, len(a2) WHERE a1 != 'SELL'
```
2. RBQL replaces all `a{i}` substrings in the query string _Q_ with `a[{i - 1}]` substrings. The result is the following string:
```
    Q = "SELECT a[2], int(a[3]) + 100, len(a[1]) WHERE a[0] != 'SELL'"
```

3. RBQL searches for "SELECT" and "WHERE" keywords in the query string _Q_, throws the keywords away, and puts everything after these keywords into two variables _S_ - select part and _W_ - where part, so we will get:
```
    S = "a[2], int(a[3]) + 100, len(a[1])"
    W = "a[0] != 'SELL'"
```

4. RBQL has static template script which looks like this:
```
    for line in sys.stdin:
        a = line.rstrip('\n').split(',')
        if %%%W_Expression%%%:
            out_fields = [%%%S_Expression%%%]
            print ','.join([str(v) for v in out_fields])
```

5. RBQL replaces `%%%W_Expression%%%` with _W_ and `%%%S_Expression%%%` with _S_ so we get the following script:
```
    for line in sys.stdin:
        a = line.rstrip('\n').split(',')
        if a[0] != 'SELL':
            out_fields = [a[2], int(a[3]) + 100, len(a[1])]
            print ','.join([str(v) for v in out_fields])
```

6. RBQL runs the patched script against user's data file: 
```
    ./tmp_script.py < data.tsv > result.tsv
```
Result set of the original query (`SELECT a3, int(a4) + 100, len(a2) WHERE a1 != 'SELL'`) is in the "result.tsv" file.  
Adding support of TOP/LIMIT keywords is trivial and to support "ORDER BY" we can introduce an intermediate array.  



### References

* [RBQL: Official Site](https://rbql.org/)
RBQL is integrated with Rainbow CSV extensions in [Vim](https://github.com/mechatroner/rainbow_csv), [VSCode](https://marketplace.visualstudio.com/items?itemName=mechatroner.rainbow-csv), [Sublime Text](https://packagecontrol.io/packages/rainbow_csv) editors.
* [RBQL in npm](https://www.npmjs.com/package/rbql): `$ npm install -g rbql`
* [RBQL in PyPI](https://pypi.org/project/rbql/): `$ pip install rbql`

