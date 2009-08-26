from exceptions import *

import xml.dom
from itertools import *

#
# XPath axes.
#

# Dictionary of all axis functions.
axes = {}

def axisfn(reverse=False, principal_node_type=xml.dom.Node.ELEMENT_NODE):
    """Axis function decorator.

    An axis function will take a node as an argument and return a sequence
    over the nodes along an XPath axis.  Axis functions have two extra
    attributes indicating the axis direction and principal node type.
    """
    def decorate(f):
        f.__name__ = f.__name__.replace('_', '-')
        f.reverse = reverse
        f.principal_node_type = principal_node_type
        axes[f.__name__] = f
        return f
    return decorate

@axisfn()
def child(node):
    return node.childNodes

@axisfn()
def descendant(node):
    for child in node.childNodes:
        for node in descendant_or_self(child):
            yield node

@axisfn()
def parent(node):
    if node.parentNode is not None:
        yield node.parentNode

@axisfn(reverse=True)
def ancestor(node):
    while node.parentNode is not None:
        node = node.parentNode
        yield node

@axisfn()
def following_sibling(node):
    while node.nextSibling is not None:
        node = node.nextSibling
        yield node

@axisfn(reverse=True)
def preceding_sibling(node):
    while node.previousSibling is not None:
        node = node.previousSibling
        yield node

@axisfn()
def following(node):
    while node is not None:
        while node.nextSibling is not None:
            node = node.nextSibling
            for n in descendant_or_self(node):
                yield n
        node = node.parentNode

@axisfn(reverse=True)
def preceding(node):
    while node is not None:
        while node.previousSibling is not None:
            node = node.previousSibling
            # Could be more efficient here.
            for n in reversed(list(descendant_or_self(node))):
                yield n
        node = node.parentNode

@axisfn(principal_node_type=xml.dom.Node.ATTRIBUTE_NODE)
def attribute(node):
    if node.attributes is not None:
        return (node.attributes.item(i)
                for i in xrange(node.attributes.length))
    return ()

@axisfn()
def namespace(node):
    raise XPathNotImplementedError("namespace axis is not implemented")

@axisfn()
def self(node):
    yield node

@axisfn()
def descendant_or_self(node):
    yield node
    for child in node.childNodes:
        for node in descendant_or_self(child):
            yield node

@axisfn(reverse=True)
def ancestor_or_self(node):
    return chain([node], ancestor(node))