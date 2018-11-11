# mkt - MaKe a Template
## motivation
originally intended to build projects with decentralized files,
mkt is now primarily geared towards versatility and readability

## command-line help

    mkt - MaKe a Template
    Usage: python mkt.py \[OPTIONS] \[TEMPLATES] \[USER-DEFINED-OPTIONS]
    OPTIONS
    	-g, --noglob	ignore globbing syntax in TEMPLATE
    	-h, --help	display this test and exit
    	-p, --populate\[=PATH]	populate PATH (if present) or the CWD
    TEMPLATES
    	the templates to execute
    	if omitted, all files in the CWD matching *.mkt are used
    USER-DEFINED-OPTIONS
    	options to execute within templates
    	these are executed in the order they are passed,
    	not the order the appear in each template

## sample template:

    title=mkt
    
    COPYING
    mkt.py
    README.md
    
    b, build:
        python -c "import mkt" # creates mkt.pyc
    c, clean:
        rm *.pyc
    i, install: # simple shell alias
        alias (title)="python $\(realpath mkt.py)" # useful escape example

## composition/syntax
mkt deals exclusively with line-based template files

any line may include comments and/or escape characters;
comment syntax:

    my line#my comment

evaluates as:

    my line

escape syntax:

    my line\#my \\comment

evaluates as:

    my line#my \comment

escape characters may also be used to wrap lines

there are 3 major types of sections: preprocessor, path, and option

preprocessor lines consist of macros,
and are ALWAYS processed individually (in sequence) EXACTLY ONCE;
definition syntax:

    my macro=some definition

expansion syntax:

    (my macro)

path lines are for packaging (AKA populating),
and are only executed by the -p or --populate arguments;
relative paths are assumed relative to the template directory;
path syntax:

    my path>another path
    my other path

copies "my path" to "another path" and "my other path" to "my other path"

option lines specify user-defined shell commands,
which are processed in the order that they are supplied by the caller;
option syntax:

    my name, other name:
        shell command
        other shell command

this evaluates

        shell command
        other shell command

(including leading whitespace) if either "my name"
or "other name" were passed by the caller;
note that all until a line without leading whitespace is encountered,
all subsequent lines are considered a part of the option
