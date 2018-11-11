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

motivation:
    originally intended to build projects with decentralized files,
    mkt is now primarily geared towards versatility and readability

sample template:
    title=mkt
    wd=.
    
    COPYING
    mkt.py
    README.md
    
    b, build:
        python -c "import mkt" # creates mkt.pyc
    c, clean:
        rm *.pyc
    i, install: # simple shell alias
        alias (title)="python $\(realpath mkt.py)" # useful escape example

composition/syntax:
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
"""

def _help():
    """print help text"""
    print "mkt - MaKe a Template\n" \
        "Usage: python mkt.py [OPTIONS] [TEMPLATES] [USER-DEFINED-OPTIONS]\n" \
        "OPTIONS\n" \
        "\t-g, --noglob\tignore globbing syntax in TEMPLATE\n" \
        "\t-h, --help\tdisplay this test and exit\n" \
        "\t-p, --populate[=PATH]\tpopulate PATH (if present) or the CWD\n" \
        "TEMPLATES\n" \
        "\tthe templates to execute\n" \
        "\tif omitted, all files in the CWD matching *.mkt are used\n" \
        "USER-DEFINED-OPTIONS\n" \
        "\toptions to execute within templates\n" \
        "\tthese are executed in the order they are passed,\n" \
        "\tnot the order the appear in each template"

def main():
    """execute from the command line"""
    dest = os.getcwd()
    no_glob = False
    populate = []
    template = None
    templates = []
    to_sort = [] # templates and user defined options
    user_defined_options = []

    for i in range(1, len(sys.argv)):
        a = sys.argv[i]
        
        if a.startswith("--"):
            stripped = a[2:]

            if stripped == "help":
                _help()
                sys.exit()
            elif stripped == "noglob":
                no_glob = True
            elif stripped == "populate":
                populate.append(os.getcwd())
            elif stripped.startswith("populate="):
                path = stripped[9:]

                if path[0] in ('\'', '\"') and path[0] == path[-1]:
                    path = path[1:-1]
                populate.append(path)
            else:
                to_sort.append(a)
        elif a.startswith('-'):
            _i = 1

            while _i < len(a):
                if a[_i] == 'g':
                    no_glob = True
                elif a[_i] == 'h':
                    _help()
                    sys.exit()
                elif a[_i] == 'p':
                    if _i == len(a) - 1:
                        populate.append(os.getcwd())
                    else:
                        populate.append(a[_i + 1:])
                        break
                _i += 1
        else:
            to_sort.append(a)

    for e in to_sort:
        if no_glob:
            if os.path.exists(e):
                templates.append(e)
            else:
                user_defined_options.append(e)
        else:
            globbed = glob.glob(e)

            if globbed:
                templates += globbed
            else:
                user_defined_options.append(e)

    if not templates:
        templates = glob.glob("*.mkt")

        if not templates:
            _help()
            sys.exit()
    
    for path in templates:
        with open(path, "rb") as fp:
            template = TemplateParser.parse(fp.read())
        
        if populate:
            for p in populate:
                template.populate(p, os.path.dirname(path))
                template.execute_options(user_defined_options, p)
        else:
            template.execute_options(user_defined_options,
                os.path.dirname(path))

def sha256file(path, buflen = 2 ** 24):
    """return the SHA-256 hash of a file"""
    sha256 = hashlib.sha256()

    with open(path, "rb") as fp:
        chunk = fp.read(buflen)

        while chunk:
            sha256.update(chunk)
            chunk = fp.read(buflen)
    return sha256.hexdigest()

class Template:
    def __init__(self, ops = (), paths = ()):
        self.ops = ops
        self.paths = paths
    
    def execute_options(self, names = (), wd = os.getcwd()):
        """execute options by name (in order of arguments)"""
        script = ["cd \"%s\"" % wd]
        selected = set()
        
        for name in names:
            for op in self.ops:
                if op.hasname(name) and not op in selected: # no repeats
                    script.append(op.script)
                    selected.union(set(op.names))
                    break
        
        if len(script) > 1:
            return os.system(os.linesep.join(script))
        return 0 # no script
    
    def populate(self, dest = os.getcwd(), src = os.getcwd()):
        """populate dest from src as needed"""
        to_copy = []

        for path in self.paths:
            dp = os.path.join(dest, path.dest)
            sp = os.path.join(src, path.src)
            
            if os.path.normpath(dp) == os.path.normpath(sp):
                continue
            elif os.path.isdir(sp):
                if os.path.exists(dp)  and not os.path.isdir(dp):
                    raise OSError("incompatible changes" \
                        " (non-directory -> directory)")
                shutil.copytree(sp, dp)
            elif os.path.isfile(sp):
                if os.path.exists(dp):
                    if not os.path.isfile(dp):
                        raise OSError("incompatible changes" \
                            " (non-file -> file)")
                    elif not sha256file(sp) == sha256file(dp):
                        shutil.copy(sp, dp)
                else:
                    shutil.copy(sp, dp)
            else:
                raise OSError("resource isn't a file or a directory")

class TemplateAttr:
    def __init__(self):
        pass

class TemplateOption(TemplateAttr):
    def __init__(self, script, *names):
        TemplateAttr.__init__(self)
        self.names = set(names)
        self.script = script

    def hasname(self, name):
        return name in self.names

class TemplateParser:
    ESCAPABLE = "\t\n\v\r #(:=>\\"
    RESERVED = "\t\n\v\r #(),:=>\\"

    class Preprocessor:
        """handles uncommenting and macros, in that order"""
        
        @staticmethod
        def expand_macros(line, macros):
            """expand macros within a line"""
            components = []
            last_end = -1 # last encountered ')'
            start = TemplateParser.find_unescaped('(', line)

            while start > -1:
                end = line.find(')', start + 1)
                
                if end == -1:
                    break
                macro = line[start + 1:end].strip()

                if macro in macros:
                    components += [line[last_end + 1:start], macros[macro]]
                    last_end = end
                start = TemplateParser.find_unescaped('(', line, start + 1)
            components.append(line[last_end + 1:])
            return ''.join(components)
        
        @staticmethod
        def extract_macro(line):
            """
            return a dictionary as such: {macro: definition},
            which may be empty
            """
            try:
                macro, definition = TemplateParser.split_unescaped('=', line,
                    1)
            except ValueError:
                return {}
            return {macro: definition}

        @staticmethod
        def preprocess(lines):
            """
            uncomment, then identify and expand macros
            
            set macro definition lines to empty lines (preserves line numbers)
            """
            if not lines:
                return lines
            macros = {}
            
            for i, line in enumerate(lines):
                line = lines[i] = TemplateParser.Preprocessor.uncomment(line)
                macro_def = TemplateParser.Preprocessor.extract_macro(line)
                
                if macro_def:
                    lines[i] = ""
                    macros.update(macro_def)

            for i, line in enumerate(lines): # must be separate
                lines[i] = TemplateParser.Preprocessor.expand_macros(line,
                    macros)
            return lines
        
        @staticmethod
        def uncomment(line):
            """uncomment a line"""
            comment_index = TemplateParser.find_unescaped('#', line)

            if comment_index > -1:
                return line[:comment_index]
            return line
    
    @staticmethod
    def escape(line):
        """escape a line"""
        if not line:
            return line
        chars = list(line)

        for i in range(len(chars) -1, -1, -1):
            c = chars[i]

            if c in TemplateParser.ESCAPABLE:
                chars.insert(i, '\\')
        return "".join(chars)
    
    @staticmethod
    def find_unescaped(needle, haystack, start = 0):
        """find an unescaped needle in a haystack"""
        if not needle:
            return 0
        escaped_needle = TemplateParser.escape(needle)
        index = haystack.find(needle, start)
        offset = len(TemplateParser.escape(needle[0])) - 1

        if not offset:
            return index
        
        while index > -1:
            escaped_index = haystack.find(escaped_needle, start)
            
            if escaped_index == -1 or not index == escaped_index + offset:
                break
            index = haystack.find(needle, index + len(needle), start)
        return index
    
    @staticmethod
    def parse(string):
        """the entry method for parsing a Template"""
        i = 0
        lines = TemplateParser.Preprocessor.preprocess(
            TemplateParser.split_unescaped(os.linesep, string))
        normalize_component = lambda c: TemplateParser.unescape(
            TemplateParser.strip_unescaped(c))
        ops = []
        paths = []

        while i < len(lines):
            line = lines[i]
            stripped = TemplateParser.strip_unescaped(line)

            if not stripped:
                pass
            elif stripped[-1] == ':': # option
                if stripped == ':':
                    i += 1
                    continue
                i += 1
                names = TemplateParser.split_unescaped(',', stripped[:-1])
                script = []

                while i < len(lines):
                    line = lines[i]
                    
                    if line:
                        if not line[0].isspace():
                            i -= 1
                            break
                        script.append(line)
                    i += 1
                ops.append(TemplateOption(os.linesep.join(
                    [normalize_component(l) for l in script]), *names))
            else: # path
                if stripped == '>':
                    i += 1
                    continue
                elif stripped.startswith('>'):
                    raise SyntaxError("no source in non-empty path" \
                        " (template line %u)" % (i + 1))
                elif TemplateParser.find_unescaped('>', stripped) == -1:
                    src = normalize_component(stripped)
                    paths.append(TemplatePath(src, src))
                else:
                    src_dest = [normalize_component(e)
                        for e in TemplateParser.split_unescaped('>', stripped,
                            1)]

                    if not src_dest[1]:
                        src_dest[1] = src_dest[0]
                    paths.append(TemplatePath(*src_dest))
            i += 1
        return Template(ops, paths)
    
    @staticmethod
    def split_unescaped(needle, haystack, nsplits = -1):
        """
        split a haystack around nsplits occurrences of a needle
        
        if nsplits < 0, split around all occurrences of a needle
        otherwise, the haystack MUST be split exactle nsplits times
        """
        indices = [TemplateParser.find_unescaped(needle, haystack)]
        split = []
        start = 0

        while not len(indices) == nsplits and not indices[-1] == -1:
            indices.append(TemplateParser.find_unescaped(needle, haystack,
                indices[-1] + len(needle)))

        if indices[-1] == -1:
            indices.pop()
        
        if nsplits >= 0 and not len(indices) == nsplits:
            raise ValueError("not enough splits")
        elif not indices:
            return [haystack]

        for i in indices:
            split.append(haystack[start:i])
            start = i + len(needle)
        split.append(haystack[indices[-1] + len(needle):])
        return split

    @staticmethod
    def strip_unescaped(string, to_strip = "\t\n\v\r "):
        """strip unescaped characters"""
        if len(string) < 2:
            return string
        back_offset = front_offset = 0
        string = string.lstrip(to_strip) # take care of leading characters
        to_strip = set(to_strip)
        
        for i in range(1, len(string)):
            if string[i - 1] == '\\' or not string[i] in to_strip:
                break
            front_offset += 1

        if front_offset == len(to_strip) - 1:
            return string[front_offset:]

        for i in range(len(string) - 2, front_offset + 1, -1):
            if string[i] == '\\' or not string[i + 1] in to_strip:
                break
            back_offset += 1
        return string[front_offset:len(string) - back_offset]
    
    @staticmethod
    def unescape(line):
        """unescape a line"""
        if len(line) < 2:
            return line
        chars = list(line)
        i = 0
        
        while i < len(chars) - 1:
            if chars[i] == '\\' and chars[i + 1] in TemplateParser.ESCAPABLE:
                del chars[i]
            else:
                i += 1
        return "".join(chars)

class TemplatePath(TemplateAttr):
    def __init__(self, src, dest):
        TemplateAttr.__init__(self)
        self.dest = dest
        self.src = src

if __name__ == "__main__":
    main()
