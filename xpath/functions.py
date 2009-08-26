from tools import *
from axes import *
from exceptions import *

import sys, math, re
from itertools import *

# A method implementing an XPath function is decorated with the function
# decorator, and receives the evaluated function arguments as positional
# parameters.
#

def function(minargs, maxargs, implicit=False, first=False, convert=None, namespaceUri=None):
    """Function decorator.

    minargs -- Minimum number of arguments taken by the function.
    maxargs -- Maximum number of arguments taken by the function.
    implicit -- True for functions which operate on a nodeset consisting
                of the current context node when passed no argument.
                (e.g., string() and number().)
    convert -- When non-None, a function used to filter function arguments.
    """
            
    def decorator(f):
        def new_f(node, pos, size, context, *args):
            if len(args) < new_f.minargs:
                raise XPathTypeError, 'too few arguments for "%s()"' % new_f.__name__
            if (new_f.maxargs is not None and
                len(args) > new_f.maxargs):
                raise XPathTypeError, 'too many arguments for "%s()"' % new_f.__name__
            
            if implicit and len(args) == 0:
                args = [[node]]

            if first:
                args = list(args)
                args[0] = nodeset(args[0])
                if len(args[0]) > 0:
                    args[0] = args[0][0]
                else:
                    args[0] = None
                    
            if convert is not None:
                if isinstance(convert, basestring):
                    cvt = lambda x: invoke(convert, node, pos, size, context, x)
                else:
                    cvt = convert
                args = [cvt(x) for x in args]
                
            return f(node, pos, size, context, *args)

        new_f.minargs = minargs
        new_f.maxargs = maxargs
        new_f.__name__ = f.__name__
        new_f.__doc__ = f.__doc__
        
        xpname = new_f.__name__[2:].replace('_', '-')
        if namespaceUri is not None:
            xpname = (namespaceUri, xpname)
        module = sys.modules[f.__module__]
        if not hasattr(module, 'xpath_functions'):
            module.xpath_functions = {}
        module.xpath_functions[xpname] = new_f
        
        return new_f
        
    return decorator

# Node Set Functions

@function(0, 0)
def f_last(node, pos, size, context):
    return size

@function(0, 0)
def f_position(node, pos, size, context):
    return pos

@function(1, 1, convert=nodeset)
def f_count(node, pos, size, context, nodes):
    return len(nodes)

@function(1, 1)
def f_id(node, pos, size, context, arg):
    if nodesetp(arg):
        ids = (string_value(x) for x in arg)
    else:
        ids = [string(arg, context)]
    if node.nodeType != node.DOCUMENT_NODE:
        node = node.ownerDocument
    return list(filter(None, (node.getElementById(id) for id in ids)))

@function(0, 1, implicit=True, first=True)
def f_local_name(node, pos, size, context, argnode):
    if argnode is None:
        return ''
    if (argnode.nodeType == argnode.ELEMENT_NODE or
        argnode.nodeType == argnode.ATTRIBUTE_NODE):
        return argnode.localName
    elif argnode.nodeType == argnode.PROCESSING_INSTRUCTION_NODE:
        return argnode.target
    return ''

@function(0, 1, implicit=True, first=True)
def f_namespace_uri(node, pos, size, context, argnode):
    if argnode is None:
        return ''
    return argnode.namespaceURI

@function(0, 1, implicit=True, first=True)
def f_name(node, pos, size, context, argnode):
    if argnode is None:
        return ''
    if argnode.nodeType == argnode.ELEMENT_NODE:
        return argnode.tagName
    elif argnode.nodeType == argnode.ATTRIBUTE_NODE:
        return argnode.name
    elif argnode.nodeType == argnode.PROCESSING_INSTRUCTION_NODE:
        return argnode.target
    return ''

# String Functions

@function(0, 1, implicit=True)
def f_string(node, pos, size, context, v):
    """Convert a value to a string."""
    
    if nodesetp(v):
        if not v:
            return u''
        return string_value(v[0])
    elif numberp(v):
        if v == float('inf'):
            return u'Infinity'
        elif v == float('-inf'):
            return u'-Infinity'
        elif str(v) == 'nan':
            return u'NaN'
        elif int(v) == v and v <= 0xffffffff:
            v = int(v)
        return unicode(v)
    elif booleanp(v):
        return u'true' if v else u'false'
    return v

@function(1, None, convert='string')
def f_concat(node, pos, size, context, *args):
    return ''.join((x for x in args))

@function(2, 2, convert='string')
def f_starts_with(node, pos, size, context, a, b):
    return a.startswith(b)

@function(2, 2, convert='string')
def f_contains(node, pos, size, context, a, b):
    return b in a

@function(2, 2, convert='string')
def f_substring_before(node, pos, size, context, a, b):
    try:
        return a[0:a.index(b)]
    except ValueError:
        return ''

@function(2, 2, convert='string')
def f_substring_after(node, pos, size, context, a, b):
    try:
        return a[a.index(b)+len(b):]
    except ValueError:
        return ''

@function(2, 3)
def f_substring(node, pos, size, context, s, start, count=None):
    s = string(s, context)
    start = round(number(start, context))
    if start != start:
        # Catch NaN
        return ''

    if count is None:
        end = len(s) + 1
    else:
        end = start + round(number(count, context))
        if end != end:
            # Catch NaN
            return ''
        if end > len(s):
            end = len(s)+1

    if start < 1:
        start = 1
    if start > len(s):
        return ''
    if end <= start:
        return ''
    return s[int(start)-1:int(end)-1]

@function(0, 1, implicit=True, convert='string')
def f_string_length(node, pos, size, context, s):
    return len(s)

@function(0, 1, implicit=True, convert='string')
def f_normalize_space(node, pos, size, context, s):
    return re.sub(r'\s+', ' ', s.strip())

@function(3, 3, convert='string')
def f_translate(node, pos, size, context, s, source, target):
    # str.translate() and unicode.translate() are completely different.
    # The translate() arguments are coerced to unicode.
    s, source, target = map(unicode, (s, source, target))
    
    table = {}
    for schar, tchar in izip(source, target):
        schar = ord(schar)
        if schar not in table:
            table[schar] = tchar
    if len(source) > len(target):
        for schar in source[len(target):]:
            schar = ord(schar)
            if schar not in table:
                table[schar] = None
    return s.translate(table)

# Boolean functions

@function(1, 1)
def f_boolean(node, pos, size, context, v):
    """Convert a value to a boolean."""
    if nodesetp(v):
        return len(v) > 0
    elif numberp(v):
        if v == 0 or v != v:
            return False
        return True
    elif stringp(v):
        return v != ''
        
    return v

@function(1, 1, convert='boolean')
def f_not(node, pos, size, context, b):
    return not b

@function(0, 0)
def f_true(node, pos, size, context):
    return True

@function(0, 0)
def f_false(node, pos, size, context):
    return False

@function(1, 1, convert='string')
def f_lang(node, pos, size, context, s):
    s = s.lower()
    for n in axes['ancestor-or-self'](node):
        if n.nodeType == n.ELEMENT_NODE and n.hasAttribute('xml:lang'):
            lang = n.getAttribute('xml:lang').lower()
            if s == lang or lang.startswith(s + u'-'):
                return True
            break
    return False

# Number functions

@function(0, 1, implicit=True)
def f_number(node, pos, size, context, v):
    """Convert a value to a number."""
    
    if nodesetp(v):
        v = string(v, context)
    try:
        return float(v)
    except ValueError:
        return float('NaN')

@function(1, 1, convert=nodeset)
def f_sum(node, pos, size, context, nodes):
    return sum((number(string_value(x), context) for x in nodes))

@function(1, 1, convert='number')
def f_floor(node, pos, size, context, n):
    return math.floor(n)

@function(1, 1, convert='number')
def f_ceiling(node, pos, size, context, n):
    return math.ceil(n)

@function(1, 1, convert='number')
def f_round(node, pos, size, context, n):
    # XXX round(-0.0) should be -0.0, not 0.0.
    # XXX round(-1.5) should be -1.0, not -2.0.
    return round(n)
    