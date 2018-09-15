# Copyright 2018 Bailey Defino
# <https://bdefino.github.io>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import glob
import hashlib
import os
import shutil
import sys

__doc__ = """
mkt - MaKe a Template

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
"""

global ESCAPABLE
ESCAPABLE = "#(,>\\"

global RESERVED # for the sake of clarity
RESERVED = "\n#(),>\\"

def _escape(string):
    """escape a string"""
    string = list(string)

    for i, c in enumerate(string):
        if c in ESCAPABLE:
            string[i] = '\\' + c
    return ''.join(string)

def _find_unescaped(haystack, needle, start = 0):
    """find the unescaped needle in the haystack"""
    for i in range(start, len(haystack)):
        if (haystack[i:i + len(needle)] == needle
                and (i == 0 or not haystack[i - 1] == '\\')):
            return i
    return -1

def _help():
    """print a help message"""
    print "MaKe a Template (into the CWD)\n" \
          "Usage: python mkt.py [OPTIONS] PATH\n" \
          "OPTIONS\n" \
          "\t-h, --help\tdisplay this text\n" \
          "\t-o, --overwrite\toverwrite the destination if it exists\n" \
          "\ttemplate-specific options are also acceptable\n" \
          "PATH\n" \
          "\ttemplate path"

def main():
    """populate and execute the necessary options"""
    dest = os.getcwd()
    i = 1
    options = []
    overwrite = False
    src = None

    while i < len(sys.argv):
        arg = sys.argv[i]
        used = False

        if arg.startswith("--"):
            _arg = arg[2:]

            if _arg == "help":
                _help()
                sys.exit()
            elif _arg == "overwrite":
                overwrite = True
            else: # unused
                options.append(arg)
        elif arg.startswith('-'):
            for c in arg[1:]:
                if c == 'h':
                    _help()
                    sys.exit()
                elif c == 'o':
                    overwrite = True
                    used = True

            if not used:
                options.append(arg)
        elif not src and os.path.exists(arg):
            src = arg
        else:
            options.append(arg)
        i += 1

    if not src:
        print "Missing source."
        _help()
        sys.exit()
    template = Template(src)
    template.execute(template.populate(os.getcwd(), overwrite), options)

def _sha256_file(path, buflen = 1048576):
    """return the SHA-256 hash for a file"""
    sha256 = hashlib.sha256()

    with open(path, "rb") as fp:
        chunk = fp.read(buflen)

        while chunk:
            sha256.update(chunk)
            chunk = fp.read(buflen)
    return sha256.hexdigest()

def _split_unescaped(haystack, needle, n = -1):
    """split haystack around unescaped occurences of needle up to n times"""
    index = _find_unescaped(haystack, needle)
    last = 0
    
    while index > -1 and not n == 0: # n < 0 -> find all
        yield haystack[last:index]
        last = index + len(needle)
        index = _find_unescaped(haystack, needle, last)
        n -= 1
    yield haystack[last:]

def _unescape(string):
    """unescape a string"""
    i = 0
    string = list(string)

    while i < len(string):
        if string[i] == '\\': # skip the next character
            del string[i]
        i += 1
    return ''.join(string)

class Macro:
    """macro parsing"""

    def __init__(self, macro = ''):
        self.definition = ''
        self.macro = macro
        index = _find_unescaped(macro, '=')

        if index > -1:
            self.definition = _unescape(macro[index + 1:])
            self.macro = _unescape(macro[:index])
        self.definition = self.definition.strip()
        self.macro = self.macro.strip()

    def expand(self, string = ''):
        """expand the current macro in a string"""
        definition = _escape(self.definition)
        expansion = "(%s)" % _escape(self.macro)
        index = _find_unescaped(string, expansion)

        while index > -1:
            string = string.replace(expansion, definition)
            index = _find_unescaped(string, expansion)
        return string

    def __str__(self):
        return '='.join((_escape(self.macro), _escape(self.definition)))

class Option:
    """
    option parser

    this class doesn't validate the subsequent commands
    """

    def __init__(self, option = ''):
        self.commands = ''
        self.opts = []
        options = list(_split_unescaped(option, '\n', 1))

        if len(options) > 1:
            self.commands = options[1]
        options = options[0]
        options = _split_unescaped(options, ',')

        for opt in options:
            opt = _unescape(opt).strip()
            
            if opt:
                self.opts.append(opt)
        self.commands = _unescape(self.commands).strip()
    
    def execute(self, options = ()):
        """
        execute the optional commands and return the exit code
        if the options specify this option

        return -1 if this option wasn't specified
        """
        for o in options:
            if o in self.opts:
                if self.commands:
                    return os.system(self.commands)
                return 0 # no command = success
        return -1

    def __str__(self):
        return '\n'.join((", ".join((_escape(o) for o
            in (self.shortopts + self.longopts))), _escape(self.commands)))

class Path:
    """path parser"""

    def __init__(self, path = ''):
        self.dest = path
        self.src = path

        if _find_unescaped(path, '>') > -1:
            self.src, dest = _split_unescaped(path, '>', 1)

            if dest.strip():
                self.dest = dest
        self.dest = _unescape(self.dest).strip()
        self.src = _unescape(self.src).strip()

        if os.path.isabs(self.dest):
            if self.dest == self.src:
                self.dest = os.path.basename(self.dest)
            else:
                raise SyntaxError("destination path cannot be absolute")
    
    def populate(self, srcwd, destwd = os.getcwd()):
        """
        srcwd/self.src -> destwd/self.dest
        
        complain about missing source(s) and failures
        """
        dest_root = os.path.join(destwd, self.dest)
        globbed = glob.glob(os.path.join(srcwd, self.src))
        assert globbed, "no source(s) match %s" % self.src
        assert (not '*' in os.path.basename(self.src)
            or '*' in os.path.basename(self.dest)), \
            "source-only globbing isn't allowed"
        
        for src in globbed:
            dest = dest_root
            src = os.path.realpath(src)

            if '*' in os.path.basename(dest):
                dest = os.path.join(os.path.dirname(dest),
                    os.path.basename(src))
            dest = os.path.realpath(dest.rstrip(os.sep))
            src = os.path.realpath(src.rstrip(os.sep))

            if dest == src:
                continue
            print src, "->", dest
            
            if not os.path.exists(os.path.dirname(dest)):
                os.makedirs(os.path.dirname(dest)) # because shutil won't
            
            if os.path.isdir(src):
                shutil.copytree(src, dest)
            else:
                shutil.copy(src, dest)
    
    def __str__(self):
        as_list = [_escape(self.src)]

        if self.dest:
            as_list.append('>')
            as_list.append(_escape(self.dest))
        return ''.join(as_list)

class Template:
    """template parsing"""
    
    def __init__(self, path = ''):
        template = ''

        with open(path, "rb") as fp:
            template = fp.read()
        self.macros = []
        self.options = []
        self.path = path
        self.paths = []
        i = 0
        lines = list(_split_unescaped(template, '\n'))

        while i < len(lines): # parse macros
            lines[i] = self._strip_comment(lines[i]) # strip comment
            l = lines[i]
            
            if _find_unescaped(l, '=') > -1:
                self.macros.append(Macro(l))
            i += 1

        for m in self.macros: # expand macros
            for i, l in enumerate(lines):
                lines[i] = m.expand(l)
        i = 0
        
        while i < len(lines):
            l = lines[i]

            if _find_unescaped(l, '=') > -1: # skip macros
                pass
            elif _find_unescaped(l, ',') > -1: # option
                option_lines = [l]

                while i < len(lines) - 1: # changing i and l saves time
                    l = lines[i + 1] # prevents skipping the first non-opt line
                    
                    if l.strip():
                        if not l[0].isspace():
                            break
                        option_lines.append(l)
                    i += 1
                self.options.append(Option('\n'.join(option_lines)))
            elif _unescape(l).strip(): # path
                self.paths.append(Path(l))
            i += 1

    def execute(self, wd = os.getcwd(), options = ()):
        """execute the template with options"""
        old_wd = os.getcwd()
        os.chdir(wd)
        
        for o in self.options:
            o.execute(options)
        os.chdir(old_wd)
    
    def populate(self, destwd = os.getcwd(), overwrite = False):
        """populate and return the destwd/(title) with the template contents"""
        srcwd = os.path.dirname(self.path)

        if os.path.realpath(destwd) == os.path.realpath(srcwd): # unnecessary
            return destwd
        
        for m in self.macros:
            if m.macro == "title" and m.definition:
                destwd = os.path.join(destwd, m.definition)
                break

        for m in self.macros:
            if m.macro == "wd" and m.definition:
                srcwd = os.path.join(srcwd, m.definition)
                break
        
        if os.path.exists(destwd):
            assert overwrite, "destination exists"
        else:
            os.makedirs(destwd)
        
        for p in self.paths:
            p.populate(srcwd, destwd)
        return destwd

    def __str__(self):
        return '\n'.join((str(e) for e in (self.macros + self.paths
            + self.options)))
    
    def _strip_comment(self, line = ''):
        """remove the comment from a line"""
        index = _find_unescaped(line, '#')

        if index > -1:
            return line[:index]
        return line

if __name__ == "__main__":
    main()
