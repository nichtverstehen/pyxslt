import xml.dom, re
import xp
import xpath.exceptions
from xslt.exceptions import *

NCNAME_RE = r'[a-zA-Z_][a-zA-Z0-9_\-\.\w]*'
QNAME_RE = r'('+NCNAME_RE+r')(?:\:('+NCNAME_RE+r'))?'
NAMETEST_RE = r'(\*)|('+NCNAME_RE+r')\:\*|'+QNAME_RE

def resolveNamespace(prefix, namespaces, resolveDefault=False):
	"""Resolves a namespace prefix using namespace bindings.
	If resolveDefault is False the result is always None for prefix=None."""
	
	if prefix is None and not resolveDefault:
		return None
	if prefix is None and None not in namespaces:
		return None
	
	try:
		return namespaces[prefix]
	except KeyError:
		raise NamespaceNotFound(prefix, prefix)
	
	
def parseQName(qname):
	"""Divides a QName into a tuple (None, str) or (str, str)"""
	
	m = re.match(QNAME_RE+'$', qname)
	if m is None:
		raise InvalidName(qname)
		
	if m.group(2) is None:
		prefix = None
		localName = m.group(1)
	else:
		prefix, localName = m.groups()
		
	return (prefix, localName)

	
def resolveQName(qname, namespaces={}, resolveDefault=False):
	"""Resolves a QName as specified in [XSLT 2.4]. 
	I.e. it doesn't resolve default namespace by default.
	Returns a tuple (namespaceUri, localName)
	Raises NamespaceNotFound id ns-prefix is not found in namespaces"""

	prefix, localName = parseQName(qname)
	namespaceUri = resolveNamespace(prefix, namespaces, resolveDefault)
	return (namespaceUri, localName)
	
	
def resolveNameTest(s, namespaces={}, resolveDefault=False):
	"""Resolves NameTest (*|NCName:*|NCName|NCName:NCName) to
	a tuple using specified namespace bindings.
	(None, None) for *, (uri, None) for NCName:*, (uri, NCName) for NCName and QName.
	It resolves defult namespaces for NCName if resolveDefault is True."""
	
	m = re.match(NAMETEST_RE+'$', s)
	if m is None:
		raise InvalidName(s)
		
	asterisk, ncname, prefix, localName = m.groups()
	
	if asterisk is not None:
		return (None, None)
	elif ncname is not None:
		prefix = ncname
		localName = None
	elif prefix is not None and localName is None:
		localName = prefix
		prefix = None
	
	namespaceUri = resolveNamespace(prefix, namespaces, resolveDefault)
		
	return (namespaceUri, localName)
	
		
def stringProperty(el, prop, default=None, required=False, choices=None):
	"""Gets a string value of an element's attribute.
	Returns default value if there is no such attribute,
	or raises AttributeRequired if it is required."""
	
	ns = None
	if isinstance(prop, tuple):
		ns, prop = prop
		
	if not el.hasAttributeNS(ns, prop) and required:
		raise AttributeRequired(el, prop)
		
	s = el.getAttributeNS(ns, prop) if el.hasAttributeNS(ns, prop) else default
	
	if choices is not None and s not in choices:
		raise InvalidAttribute(el, prop, s)
		
	return s

	
def floatProperty(el, prop, default=None, required=False):
	"""Gets a float value of an attribute.
	Raises InvalidAttribute if it isn't a number or AttributeRequired.
	Default value must be float or None."""
	
	s = stringProperty(el, prop, required=required)
	
	try:
		s = float(s) if s is not None else default
	except ValueError, e:
		raise InvalidAttribute(el, prop, s, e)
		
	return s
	
	
def boolProperty(el, prop, default=False, required=False):
	"""Gets a bool value of an attribute ("yes"|"no" => True|False).
	Raises InvalidAttribute if it is not yes/no, or AttributeRequired.
	Default value must be bool or None."""
	
	s = stringProperty(el, prop, required=required)
	if s is None:
		return default
		
	if s == 'yes':
		return True
	elif s == 'no':
		return False
	else:
		raise InvalidAttribute(el, prop, s)
	
	
def qnameProperty(el, prop, namespaces={}, default=None, required=False, resolveDefault=False):
	"""Constructs a QName tuple value from an attribute.
	Raises InvalidAttribute if QName is invalid, or AttributeRequired.
	Default value must be QName string or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
	
	try:
		s = resolveQName(s, namespaces, resolveDefault) if s is not None else None
	except InvalidName, e:
		raise InvalidAttribute(el, prop, e.name, e)
	
	return s
	
	
def qnameListProperty(el, prop, namespaces={}, default=None, required=False, resolveDefault=False):
	"""Constructs a list of QName tuples from an attribute.
	Raises InvalidAttribute if QName is invalid, or AttributeRequired.
	Default value must be string of QNames or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
	if s is None:
		return None
		
	g = s.split()
	
	try:
		g = [resolveQName(i, namespaces, resolveDefault) for i in g]
	except InvalidName, e:
		raise InvalidAttribute(el, prop, e.name, e)
		
	return g
	
	
def nameTestListProperty(el, prop, namespaces={}, default=None, required=False, resolveDefault=False):
	"""Constructs a list of NameTest tuples from an attribute.
	Raises InvalidAttribute if NameTest is invalid, or AttributeRequired.
	Default value must be string of NameTests or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
	if s is None:
		return None
		
	g = s.split()
	
	try:
		g = [resolveNameTest(i, namespaces, resolveDefault) for i in g]
	except InvalidName, e:
		raise InvalidAttribute(el, prop, e.name, e)
		
	return g
	
	
def nsPrefixProperty(el, prop, namespaces={}, default=None, required=False):
	"""Gets namespace URI of namespace specified by an attribute 
	(or default namespace if it is '#default').
	Raises InvalidAttribute if prefix can't be resolved, or AttributeRequired.
	Default value must be ns-prefix string or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
	if s is None:
		return None
		
	if s == '#default':
		s = None
		
	g = resolveNamespace(s, namespaces, True)
	
	return g
	
	
def nsListProperty(el, prop, namespaces={}, default=None, required=False):
	"""Gets a list of ns URIs specified by an attribute.
	Raises InvalidAttribute if any prefix can't be resolved, or AttributeRequired.
	Default value must be a string (space-delimited prefixed) or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
	
	if s is None:
		return None
		
	g = s.split()
	g = [i if i != '#default' else None for i in g]
	
	g = [resolveNamespace(i, namespaces, True) for i in g]
		
	return g
	
	
def exprProperty(el, prop, default=None, required=False):
	"""Constructs an XPath from an attribute.
	Raises InvalidAttribute if xpath is invalid, or AttributeRequired.
	Default value must be xpath string or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
		
	try:
		s = xp.XPath(s) if s is not None else None
	except xpath.exceptions.XPathParseError, e:
		raise InvalidAttribute(el, prop, s, e)
		
	return s
	
	
def attributeTemplateProperty(el, prop, default=None, required=False):
	"""Constructs an AttributeTemplate from an attribute.
	Raises InvalidAttribute if xpath is invalid, or AttributeRequired.
	Default value must be a string or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
		
	try:
		s = xp.AttributeTemplate(s) if s is not None else None
	except xpath.exceptions.XPathParseError, e:
		raise InvalidAttribute(el, prop, s, e)
		
	return s
	
	
def patternProperty(el, prop, default=None, required=False):
	"""Constructs a Pattern from an attribute.
	Raises InvalidAttribute if pattern is invalid, or AttributeRequired.
	Default value must be pattern string or None."""
	
	s = stringProperty(el, prop, default=default, required=required)
	
	try:
		s = xp.Pattern(s) if s is not None else None
	except xpath.exceptions.XPathParseError, e:
		raise InvalidAttribute(el, prop, s, e)
		
	return s
	