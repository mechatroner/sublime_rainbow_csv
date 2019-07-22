![logo](https://i.imgur.com/cJwEvyM.png)

# Rainbow CSV

### Main features

* Highlight columns in *.csv, *.tsv and other separated files in different rainbow colors.
* Provide info about columns on mouse hover.
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
Allowed values: _"Python"_, _"JS"_  
In order to use RBQL with JavaScript (JS) you need to have Node JS installed and added to your system path.  

#### "rbql_output_format"
Format of RBQL result set tables.  
Allowed values: _"tsv"_, _"csv"_, _"input"_  
* input: same format as the input table
* tsv: tab separated values.
* csv: is Excel-compatible and allows quoted commas.

Example: to always use "tsv" as output format add this line to your settings file: `"rbql_output_format": "tsv",`


### References

* This Sublime Text plugin is an adaptation of Vim's rainbow_csv [plugin](https://github.com/mechatroner/rainbow_csv)


# RBQL (RainBow Query Language) Description
RBQL is a technology which provides SQL-like language that supports _SELECT_ and _UPDATE_ queries with Python or JavaScript expressions.  

[Official Site](https://rbql.org/)

### Main Features
* Use Python or JavaScript expressions inside _SELECT_, _UPDATE_, _WHERE_ and _ORDER BY_ statements
* Result set of any query immediately becomes a first-class table on it's own.
* Output entries appear in the same order as in input unless _ORDER BY_ is provided.
* Input csv/tsv spreadsheet may contain varying number of entries (but select query must be written in a way that prevents output of missing values)
* Works out of the box, no external dependencies.

### Supported SQL Keywords (Keywords are case insensitive)

* SELECT \[ TOP _N_ \] \[ DISTINCT [ COUNT ] \]
* UPDATE \[ SET \]
* WHERE
* ORDER BY ... [ DESC | ASC ]
* [ [ STRICT ] LEFT | INNER ] JOIN
* GROUP BY
* LIMIT _N_

#### Keywords rules
All keywords have the same meaning as in SQL queries. You can check them [online](https://www.w3schools.com/sql/default.asp)  
But there are also two new keywords: _DISTINCT COUNT_ and _STRICT LEFT JOIN_:  
* _DISTINCT COUNT_ is like _DISTINCT_, but adds a new column to the "distinct" result set: number of occurences of the entry, similar to _uniq -c_ unix command.
* _STRICT LEFT JOIN_ is like _LEFT JOIN_, but generates an error if any key in left table "A" doesn't have exactly one matching key in the right table "B".

Some other rules:
* _UPDATE SET_ is synonym to _UPDATE_, because in RBQL there is no need to specify the source table.
* _UPDATE_ has the same semantic as in SQL, but it is actually a special type of _SELECT_ query.
* _JOIN_ statements must have the following form: _<JOIN\_KEYWORD> (/path/to/table.tsv | table_name ) ON ai == bj_
* _TOP_ and _LIMIT_ have identical semantic.

### Special variables

| Variable Name          | Variable Type | Variable Description                 |
|------------------------|---------------|--------------------------------------|
| _a1_, _a2_,..., _a{N}_   |string         | Value of i-th column                 |
| _b1_, _b2_,..., _b{N}_   |string         | Value of i-th column in join table B |
| _NR_                     |integer        | Line number (1-based)                |
| _NF_                     |integer        | Number of fields in line             |

### Aggregate functions and queries
RBQL supports the following aggregate functions, which can also be used with _GROUP BY_ keyword:  
_COUNT()_, _MIN()_, _MAX()_, _SUM()_, _AVG()_, _VARIANCE()_, _MEDIAN()_

**Limitations:**
* Aggregate function are CASE SENSITIVE and must be CAPITALIZED.
* It is illegal to use aggregate functions inside Python (or JS) expressions. Although you can use expressions inside aggregate functions.
  E.g. `MAX(float(a1) / 1000)` - legal; `MAX(a1) / 1000` - illegal.

### Examples of RBQL queries

#### With Python expressions

* `select top 100 a1, int(a2) * 10, len(a4) where a1 == "Buy" order by int(a2)`
* `select * order by random.random()` - random sort, this is an equivalent of bash command _sort -R_
* `select top 20 len(a1) / 10, a2 where a2 in ["car", "plane", "boat"]` - use Python's "in" to emulate SQL's "in"
* `select len(a1) / 10, a2 where a2 in ["car", "plane", "boat"] limit 20`
* `update set a3 = 'US' where a3.find('of America') != -1`
* `select * where NR <= 10` - this is an equivalent of bash command "head -n 10", NR is 1-based')
* `select a1, a4` - this is an equivalent of bash command "cut -f 1,4"
* `select * order by int(a2) desc` - this is an equivalent of bash command "sort -k2,2 -r -n"
* `select NR, *` - enumerate lines, NR is 1-based
* `select * where re.match(".*ab.*", a1) is not None` - select entries where first column has "ab" pattern
* `select a1, b1, b2 inner join ./countries.txt on a2 == b1 order by a1, a3` - an example of join query
* `select distinct count len(a1) where a2 != 'US'`
* `select MAX(a1), MIN(a1) where a2 != 'US' group by a2, a3`

#### With JavaScript expressions

* `select top 100 a1, a2 * 10, a4.length where a1 == "Buy" order by parseInt(a2)`
* `select * order by Math.random()` - random sort, this is an equivalent of bash command _sort -R_
* `select top 20 a1.length / 10, a2 where ["car", "plane", "boat"].indexOf(a2) > -1`
* `select a1.length / 10, a2 where ["car", "plane", "boat"].indexOf(a2) > -1 limit 20`
* `update set a3 = 'US' where a3.indexOf('of America') != -1`
* `select * where NR <= 10` - this is an equivalent of bash command "head -n 10", NR is 1-based')
* `select a1, a4` - this is an equivalent of bash command "cut -f 1,4"
* `select * order by parseInt(a2) desc` - this is an equivalent of bash command "sort -k2,2 -r -n"
* `select NR, *` - enumerate lines, NR is 1-based
* `select a1, b1, b2 inner join ./countries.txt on a2 == b1 order by a1, a3` - an example of join query
* `select distinct count a1.length where a2 != 'US'`
* `select MAX(a1), MIN(a1) where a2 != 'US' group by a2, a3`


### FAQ

#### How does RBQL work?
Python module rbql.py parses RBQL query, creates a new python worker module, then imports and executes it.

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
        a = line.rstrip('\n').split('\t')
        if %%%W_Expression%%%:
            out_fields = [%%%S_Expression%%%]
            print '\t'.join([str(v) for v in out_fields])
```

5. RBQL replaces `%%%W_Expression%%%` with _W_ and `%%%S_Expression%%%` with _S_ so we get the following script:
```
    for line in sys.stdin:
        a = line.rstrip('\n').split('\t')
        if a[0] != 'SELL':
            out_fields = [a[2], int(a[3]) + 100, len(a[1])]
            print '\t'.join([str(v) for v in out_fields])
```

6. RBQL runs the patched script against user's data file: 
```
    ./tmp_script.py < data.tsv > result.tsv
```
Result set of the original query (`SELECT a3, int(a4) + 100, len(a2) WHERE a1 != 'SELL'`) is in the "result.tsv" file.
It is clear that this simplified version can only work with tab-separated files.


#### Is this technology reliable?
It should be: RBQL scripts have only 1000 - 2000 lines combined (depending on how you count them) and there are no external dependencies.
There is no complex logic, even query parsing functions are very simple. If something goes wrong RBQL will show an error instead of producing incorrect output, also there are currently 5 different warning types.


### Standalone CLI Apps

You can also use two standalone RBQL Apps: with JavaScript and Python backends

#### rbql-js
Installation: `$ npm i rbql`  
Usage: `$ rbql-js --query "select a1, a2 order by a1" < input.tsv`  

#### rbql-py
Installation: `$ pip install rbql`  
Usage: `$ rbql-py --query "select a1, a2 order by a1" < input.tsv`  

