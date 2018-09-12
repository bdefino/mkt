# mkt - MaKe a Template

## motivation

I've always had a distaste for `Make`'s syntax, so I tried to make a similar
tool geared towards readability and package decentralization

`mkt` is a bare-bones approach with 2 main functions:
grouping packages, and executing optional commands;
see below for details

## syntax

a template is a line-based build/packaging format which consists of
comments, macros, options, and paths

templates use the standard ASCII character set, but reserve the '\n', '#',
'(', ')', ',', '>', and '\\' characters;

to escape one of these characters, it must be immediately prefaced
with a backslash character: the only exception being ')',
which doesn't need to be escaped;
this behavior may also be used for line extension

e.g.

    not a comment # comment?

    \# comment?

    \(macro?)

    line 1 \

    line 2

becomes

    not a comment

    # comment?

    (macro?)

    line 1 line 2

comments are prefaced with the pound sign, and may occur at any point
within a line

e.g.

    # this line is commented

    some other line # I'm a comment

is interpreted as

    some other line

macros are declared using the equals sign,
and are expanded by wrapping their case-and-space-sensitive names
with parentheses

e.g.

    my macro=some value

    (my macro)

    (mY mAcRo)

    ( my macro )

becomes

    my macro=some value

    some value

    (mY mAcRo)

    ( my macro )

there are two special macro names: "title" and "wd", which repectively define
a template's title and the working directory to find source files

options are comma-separated (and need at least one comma to be recognized),
and may contain muliple occurences
and redefinitions of option values;

every non-empty line following the option is considered a command,
so long as it begins with a whitespace character

e.g.

    opt,
    
        my command
        
executes "my command" whenever the option "opt" is supplied

paths are lines which don't match either the macro or option conventions;
the greater than sign may be used to redefine a path

e.g.

    path/to/file

    path/to/file>

    path/to/file>new/local/path

is equivalent to

    cp (wd)/path/to/file other-directory/

    cp (wd)/path/to/file other-directory/

    cp (wd)/path/to/file other-directory/new/local/path

when an the source is absolute, and matches the destination, the basename
component is used as the destination;
when the destination path is absolute, and differs from the source path,
a SyntaxError is raised

e.g.

    /absolute/path

    /absolute/path>/other/absolute/path

    /absolute/path>relative/path

is equivalent to

    cp /absolute/path other-directory/path

    SyntaxError

    cp /absolute/path other-directory/relative/path

file globbing is only evaluated when the source path contains globbing;
if the source path uses file globbing and the destination path has no
globbing in its basename component (after the final slash),
a SyntaxError is raised;
when the destination path uses file globbing, and any non-asterisk characters
are present, the basename becomes a single asterisk (i.e. accepts all globbed
paths)

e.g.

    path/to/files/*

    path/to/files/*>new/local/path

    path/to/files/*>new/local/paths*

is interpreted as

    cp (wd)/path/to/files/* other-directory/path/to/files/*

    SyntaxError

    cp (wd)/path/to/files/* other-directory/new/local/*

# sample template

    # an example template for this very program
    title=mkt
    wd=. # default source WD
    lang=Python 2

    COPYING # GPL 3 license
    (title).py

    s, show-help # show the help text for this program
        python2 (title).py -h

# command-line help

    MaKe a Template (into the CWD)
    Usage: python mkt.py [OPTIONS] PATH
    OPTIONS
	    -h, --help	display this text
	    -o, --overwrite	overwrite the destination if it exists
	    template-specific options are also acceptable
    PATH
	    template path
