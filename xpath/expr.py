from __future__ import division
from itertools import *
import math
import operator
import xml.dom
import weakref

from xpath.exceptions import *
from tools import *
from axes import *


#
# Data model functions.
#

def document_order(node):
    """Compute a document order value for the node.
    
    cmp(document_order(a), document_order(b)) will return -1, 0, or 1 if
    a is before, identical to, or after b in the document respectively.

    We represent document order as a list of sibling indexes.  That is,
    the third child of the document node has an order of [2].  The first
    child of that node has an order of [2,0].

    Attributes have a sibling index of -1 (coming before all children of
    their node) and are further ordered by name--e.g., [2,0,-1,'href'].

    """

    # Attributes: parent-order + [-1, attribute-name]
    if node.nodeType == node.ATTRIBUTE_NODE:
        order = document_order(node.ownerElement)
        order.extend((-1, node.name))
        return order

    # The document root (hopefully): []
    if node.parentNode is None:
        return [hash(node)] # set some order for different documents

    # Determine which child this is of its parent.
    sibpos = 0
    sib = node
    while sib.previousSibling is not None:
        sibpos += 1
        sib = sib.previousSibling

    # Order: parent-order + [sibling-position]
    order = document_order(node.parentNode)
    order.append(sibpos)
    return order

#
# Internally, we use the following representations:
#       nodeset - list of DOM tree nodes in document order
#       string  - str or unicode
#       boolean - bool
#       number  - int or float
#

class Expr(object):
    """Abstract base class for XPath expressions."""

    def evaluate(self, node, pos, size, context):
        """Evaluate the expression.

        The context node, context position, and context size are passed as
        arguments.

        Returns an XPath value: a nodeset, string, boolean, or number.

        """

class BinaryOperatorExpr(Expr):
    """Base class for all binary operators."""

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def evaluate(self, node, pos, size, context):
        # Subclasses either override evaluate() or implement operate().
        return self.operate(self.left.evaluate(node, pos, size, context),
                            self.right.evaluate(node, pos, size, context))

    def __str__(self):
        return '(%s %s %s)' % (self.left, self.op, self.right)

class AndExpr(BinaryOperatorExpr):
    """<x> and <y>"""

    def evaluate(self, node, pos, size, context):
        evaluateOp = lambda x: invoke('boolean', node, pos, size, context, x.evaluate(node, pos, size, context))
        # Note that XPath boolean operations short-circuit.
        return (evaluateOp(self.left) and
                evaluateOp(self.right))

class OrExpr(BinaryOperatorExpr):
    """<x> or <y>"""

    def evaluate(self, node, pos, size, context):
        evaluateOp = lambda x: invoke('boolean', node, pos, size, context, x.evaluate(node, pos, size, context))
        
        # Note that XPath boolean operations short-circuit.
        return (evaluateOp(self.left) or evaluateOp(self.right))

class EqualityExpr(BinaryOperatorExpr):
    """<x> = <y>, <x> != <y>, etc."""

    operators = {
        '='  : operator.eq,
        '!=' : operator.ne,
        '<=' : operator.le,
        '<'  : operator.lt,
        '>=' : operator.ge,
        '>'  : operator.gt,
    }

    def evaluate(self, node, pos, size, context):
        a = self.left.evaluate(node, pos, size, context)
        b = self.right.evaluate(node, pos, size, context)
        
        return self.operateImpl(a, b, node, pos, size, context)
            
    def operateImpl(self, a, b, node, pos, size, context):
        if nodesetp(a):
            for node in a:
                if self.operateImpl(string_value(node), b, node, pos, size, context):
                    return True
            return False

        if nodesetp(b):
            for node in b:
                if self.operateImpl(a, string_value(node), node, pos, size, context):
                    return True
            return False
            
        if self.op in ('=', '!='):
            if booleanp(a) or booleanp(b):
                convert = 'boolean'
            elif numberp(a) or numberp(b):
                convert = 'number'
            else:
                convert = 'string'
        else:
            convert = 'number'

        a, b = map(lambda x: invoke(convert, node, pos, size, context, x), (a,b))
        return self.operators[self.op](a, b)

def divop(x, y):
    try:
        return x / y
    except ZeroDivisionError:
        if x == 0 and y == 0:
            return float('nan')
        if x < 0:
            return float('-inf')
        return float('inf')

class ArithmeticalExpr(BinaryOperatorExpr):
    """<x> + <y>, <x> - <y>, etc."""

    # Note that we must use math.fmod for the correct modulo semantics.
    operators = {
        '+'   : operator.add,
        '-'   : operator.sub,
        '*'   : operator.mul,
        'div' : divop,
        'mod' : math.fmod
    }

    def evaluate(self, node, pos, size, context):
        evaluateOp = lambda x: invoke('number', node, pos, size, context, x.evaluate(node, pos, size, context))
        return self.operators[self.op](evaluateOp(self.left), evaluateOp(self.right))

class UnionExpr(BinaryOperatorExpr):
    """<x> | <y>"""

    def operate(self, a, b):
        if not nodesetp(a) or not nodesetp(b):
            raise XPathTypeError("union operand is not a node-set")

        # Need to sort the result to preserve document order.
        return sorted(set(chain(a, b)), key=document_order)

class NegationExpr(Expr):
    """- <x>"""

    def __init__(self, expr):
        self.expr = expr

    def evaluate(self, node, pos, size, context):
        return -number(self.expr.evaluate(node, pos, size, context), context)

    def __str__(self):
        return '(-%s)' % self.expr

class LiteralExpr(Expr):
    """Literals--either numbers or strings."""

    def __init__(self, literal):
        self.literal = literal

    def evaluate(self, node, pos, size, context):
        return self.literal

    def __str__(self):
        if isinstance(self.literal, basestring):
            if "'" in self.literal:
                return '"%s"' % self.literal
            else:
                return "'%s'" % self.literal
        return unicode(self.literal)

class VariableReference(Expr):
    """Variable references."""

    def __init__(self, prefix, name):
        self.prefix = prefix
        self.name = name

    def evaluate(self, node, pos, size, context):
        try:
            if self.prefix is not None:
                try:
                    namespaceURI = context.namespaces[self.prefix]
                except KeyError:
                    raise XPathUnknownPrefixError(self.prefix)
                return context.variables[(namespaceURI, self.name)]
            else:
                return context.variables[(None, self.name)]
        except KeyError:
            raise XPathUnknownVariableError(str(self))

    def __str__(self):
        if self.prefix is None:
            return '$%s' % self.name
        else:
            return '$%s:%s' % (self.prefix, self.name)

class Function(Expr):
    """Functions."""

    def __init__(self, name, args):
        spl = name.split(':')
        
        if len(spl) == 1:
            self.name = name
            self.prefix = None
        else:
            self.name = spl[1]
            self.prefix = spl[0]
            
        self.args = args
            
    def evaluate(self, node, pos, size, context):
        args = [x.evaluate(node, pos, size, context) for x in self.args]
        
        if self.prefix is not None:
            try:
                namespaceURI = context.namespaces[self.prefix]
            except KeyError:
                raise XPathUnknownPrefixError(self.prefix)
            name = (namespaceURI, self.name)
        else:
            name = self.name
            
        return invoke(name, node, pos, size, context, *args)

    def __str__(self):
        return '%s(%s)' % (self.name, ', '.join((str(x) for x in self.args)))

def merge_into_nodeset(target, source):
    """Place all the nodes from the source node-set into the target
    node-set, preserving document order.  Both node-sets must be in
    document order to begin with.

    """
    if len(target) == 0:
        target.extend(source)
        return

    source = [n for n in source if n not in target]
    if len(source) == 0:
        return

    # If the last node in the target set comes before the first node in the
    # source set, then we can just concatenate the sets.  Otherwise, we
    # will need to sort.  (We could also check to see if the last node in
    # the source set comes before the first node in the target set, but this
    # situation is very unlikely in practice.)
    if document_order(target[-1]) < document_order(source[0]):
        target.extend(source)
    else:
        target.extend(source)
        target.sort(key=document_order)

class AbsolutePathExpr(Expr):
    """Absolute location paths."""

    def __init__(self, path):
        self.path = path

    def evaluate(self, node, pos, size, context):
        if node.nodeType != node.DOCUMENT_NODE:
            node = node.ownerDocument
        if self.path is None:
            return [node]
        return self.path.evaluate(node, 1, 1, context)

    def __str__(self):
        return '/%s' % (self.path or '')

class PathExpr(Expr):
    """Location path expressions."""

    def __init__(self, steps):
        self.steps = steps

    def evaluate(self, node, pos, size, context):
        # The first step in the path is evaluated in the current context.
        # If this is the only step in the path, the return value is
        # unimportant.  If there are other steps, however, it must be a
        # node-set.
        result = self.steps[0].evaluate(node, pos, size, context)
        if len(self.steps) > 1 and not nodesetp(result):
            raise XPathTypeError("path step is not a node-set")

        # Subsequent steps are evaluated for each node in the node-set
        # resulting from the previous step.
        for step in self.steps[1:]:
            aggregate = []
            for i in xrange(len(result)):
                nodes = step.evaluate(result[i], i+1, len(result), context)
                if not nodesetp(nodes):
                    raise XPathTypeError("path step is not a node-set")
                merge_into_nodeset(aggregate, nodes)
            result = aggregate

        return result

    def __str__(self):
        return '/'.join((str(s) for s in self.steps))

class PredicateList(Expr):
    """A list of predicates.
    
    Predicates are handled as an expression wrapping the expression
    filtered by the predicates.

    """
    def __init__(self, expr, predicates, axis='child'):
        self.predicates = predicates
        self.expr = expr
        self.axis = axes[axis]

    def evaluate(self, node, pos, size, context):
        result = self.expr.evaluate(node, pos, size, context)
        if not nodesetp(result):
            raise XPathTypeError("predicate input is not a node-set")

        if self.axis.reverse:
            result.reverse()

        for pred in self.predicates:
            match = []
            for i, node in izip(count(1), result):
                r = pred.evaluate(node, i, len(result), context)

                # If a predicate evaluates to a number, select the node
                # with that position.  Otherwise, select nodes for which
                # the boolean value of the predicate is true.
                if numberp(r):
                    if r == i:
                        match.append(node)
                elif invoke('boolean', node, pos, size, context, r):
                    match.append(node)
            result = match

        if self.axis.reverse:
            result.reverse()

        return result

    def __str__(self):
        s = str(self.expr)
        if '/' in s:
            s = '(%s)' % s
        return s + ''.join(('[%s]' % x for x in self.predicates))

class AxisStep(Expr):
    """One step in a location path expression."""

    def __init__(self, axis, test=None, predicates=None):
        if test is None:
            test = AnyKindTest()
        self.axis = axes[axis]
        self.test = test

    def evaluate(self, node, pos, size, context):
        match = []
        for n in self.axis(node):
            if self.test.match(n, self.axis, context):
                match.append(n)

        if self.axis.reverse:
            match.reverse()

        return match

    def __str__(self):
        return '%s::%s' % (self.axis.__name__, self.test)

#
# Node tests.
#

class Test(object):
    """Abstract base class for node tests."""

    def match(self, node, axis, context):
        """Return True if 'node' matches the test along 'axis'."""

class NameTest(object):
    def __init__(self, prefix, localpart):
        self.prefix = prefix
        self.localName = localpart
        if self.prefix == None and self.localName == '*':
            self.prefix = '*'

    def match(self, node, axis, context):
        if node.nodeType != axis.principal_node_type:
            return False

        if self.prefix != '*':
            namespaceURI = None
            if self.prefix is not None:
                try:
                    namespaceURI = context.namespaces[self.prefix]
                except KeyError:
                    raise XPathUnknownPrefixError(self.prefix)
            elif axis.principal_node_type == node.ELEMENT_NODE:
                namespaceURI = context.namespaces.get(None)
            if namespaceURI != node.namespaceURI:
                return False
        if self.localName != '*':
            if self.localName != node.localName:
                return False
        return True

    def __str__(self):
        if self.prefix is not None:
            return '%s:%s' % (self.prefix, self.localName)
        else:
            return self.localName

class PITest(object):
    def __init__(self, name=None):
        self.name = name

    def match(self, node, axis, context):
        return (node.nodeType == node.PROCESSING_INSTRUCTION_NODE and
                (self.name is None or node.target == self.name))

    def __str__(self):
        if self.name is None:
            name = ''
        elif "'" in self.name:
            name = '"%s"' % self.name
        else:
            name = "'%s'" % self.name
        return 'processing-instruction(%s)' % name

class CommentTest(object):
    def match(self, node, axis, context):
        return node.nodeType == node.COMMENT_NODE

    def __str__(self):
        return 'comment()'

class TextTest(object):
    def match(self, node, axis, context):
        return node.nodeType == node.TEXT_NODE

    def __str__(self):
        return 'text()'

class AnyKindTest(object):
    def match(self, node, axis, context):
        return True

    def __str__(self):
        return 'node()'
