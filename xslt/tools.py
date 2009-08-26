#from xslt import XSLT_NAMESPACE
#from core import XSLT_NAMESPACE
from xslt.exceptions import *
from StringIO import StringIO
import xml.dom

class ClassInitializer(type):
	def __init__(cls, name, bases, dict):
		cls._init_class(cls, name, bases, dict)
		
def formatQName(qnameTuple):
	if qnameTuple[0] is not None:
		return '%s:%s' % qnameTuple
	else:
		return qnameTuple[1]
	
def getNamespaceBindings(element):
	"""Gets a dict of namespace binding defined for an element 
	using xmlns: attributes."""
	
	namespaces = {}
	for i in range(element.attributes.length):
		attr = element.attributes.item(i)
		if attr.namespaceURI == xml.dom.XMLNS_NAMESPACE:
			if attr.localName == 'xmlns':
				namespaces[None] = attr.value
			else:
				namespaces[attr.localName] = attr.value
	return namespaces

	
def isWhitespaceNode(node):
	"""Check if node is a Text node and consists 
	of just \t\r\n or space [XSLT 3.4]"""
	
	import re
	return node.nodeType == xml.dom.Node.TEXT_NODE and \
		bool(re.match(r'[ \t\r\n]*$', node.data))
	
	
def childElements(node):
	"""Returns a list of all child Elements of node. 
	If the node has any child nodes that are not Element 
	or whitespace raises UnexpectedNode"""
	
	elements = []
	for i in node.childNodes:
		if i.nodeType == xml.dom.Node.ELEMENT_NODE:
			elements.append(i)
		elif isWhitespaceNode(i):
			pass # ignore
		else:
			raise UnexpectedNode(i)
	return elements
	
	
def isNameTestInList(test, l):
	"""Tests if NameTest is allowed in NameTest list.
	Wildcards are allowed so that
	(NCName, None) allows (NCName, NCName) and (NCName, None)
	and (None, None) allows (None, None), (NCName, None) and (NCName, NCName)"""
	
	return test in l or \
		(test[0], None) in l or \
		(None, None) in l
		
		
def stripSpace(node, stripSpaceList=[], preserveSpaceList=[], defaultStrip=True, stripComments=True, active=True, currentActive=True):
	"""Removes descendant whitespace nodes according to [XSLT 3.4].
	stripSpace and preserveSpace are lists of NameTests. NameTests from preserveSpace take precednce.
	Setting active to False turns off whitespace stripping by default 
	(a descendant with xml:space="default" will turn it on).
	Setting currentActive to False turns off whitespace strippng just for node itself.
	currentActive is indicating that node's parent is in set of whitespace-preserving elements.
	If defaultStrip is True an element is considered whitespace-stripping by default (as in XML)
	If defaultStrip is False an element is whitespace-preserving by default (as in [XSLT 4.3] for source docs)"""
	
	if node.nodeType == xml.dom.Node.TEXT_NODE:
		if active and currentActive and isWhitespaceNode(node):
			node.parentNode.removeChild(node)
			
	elif node.nodeType == xml.dom.Node.ELEMENT_NODE:
		if node.getAttributeNS(xml.dom.XML_NAMESPACE, 'space') == 'preserve':
			active = False
		if node.getAttributeNS(xml.dom.XML_NAMESPACE, 'space') == 'default':
			active = True
			
		currentActive = defaultStrip
		if isNameTestInList((node.namespaceURI, node.localName), stripSpaceList):
			currentActive = True
		if isNameTestInList((node.namespaceURI, node.localName), preserveSpaceList):
			currentActive = False
			
		childNodes = list(node.childNodes) # save ChildNodes. deleting a child will modify node.childNodes
		for child in childNodes:
			stripSpace(child, stripSpaceList, preserveSpaceList, active=active, currentActive=currentActive)
			
	elif node.nodeType == xml.dom.Node.COMMENT_NODE and stripComments:
		node.parentNode.removeChild(node)
		
		
def pushResult(value, result):
	"""Adds value as a child to result or concatenate value to result.
	result can be basestring, Attr, Text, Comment, CDATASection, ProcessingInstruction,
	Element, DocumentFragment, Document.
	value can be basestring or any Node or list of them.
	Returns modified result."""
	
	if type(value) is list:
		for v in value:
			result = pushResult(v, result)
		return result
		
	if isinstance(result, StringIO) or \
			result.nodeType in [xml.dom.Node.ATTRIBUTE_NODE, xml.dom.Node.TEXT_NODE, \
			xml.dom.Node.COMMENT_NODE, xml.dom.Node.CDATA_SECTION_NODE, \
			xml.dom.Node.PROCESSING_INSTRUCTION_NODE]:
		# if result accepts only text
		if isinstance(value, xml.dom.Node) and value.nodeType == xml.dom.Node.TEXT_NODE:
			value = value.data
		if not isinstance(value, basestring):
			raise InvalidContent(value)
			
		if isinstance(result, StringIO):
			result.write(unicode(value))
		elif result.nodeType == xml.dom.Node.ATTRIBUTE_NODE:
			result.value += unicode(value)
		else:
			result.data += unicode(value)
			
		return result
		
	if isinstance(result, xml.dom.Node):
		if result.nodeType in [xml.dom.Node.ELEMENT_NODE,
				xml.dom.Node.DOCUMENT_FRAGMENT_NODE, xml.dom.Node.DOCUMENT_NODE]:
			
			if isinstance(value, xml.dom.Node) and \
					value.nodeType == xml.dom.Node.ATTRIBUTE_NODE:
				if result.nodeType != xml.dom.Node.ELEMENT_NODE or \
						result.childNodes.length > 0:
					raise UnexpectedAttribute(value)
				result.setAttributeNode(value)
				return result
				
			if isinstance(value, basestring):
				value = result.ownerDocument.createTextNode(value)
			if isinstance(value, xml.dom.Node) and \
					value.nodeType == xml.dom.Node.DOCUMENT_NODE:
				value = value.documentElement
			resultDocument = result.ownerDocument \
								if result.nodeType != xml.dom.Node.DOCUMENT_NODE \
								else result
			if value.ownerDocument != resultDocument:
				value = resultDocument.importNode(value, True)
			
			result.appendChild(value)
			
			return result
			
		else:
			raise InvalidContent(value)

			
def safeUpdateDict(a, b):
	"""Updates dict a preserving values for existing keys"""
	
	for (k, v) in b.iteritems():
		if not a.has_key(k):
			a[k] = v
			
			
def combineOutput(output, newvalues):
	"""Combines two dicts containing the values of xsl:output attributes
	as specified in [XSLT 16.0]."""
	
	# merge cdata-section-elements
	if newvalues.has_key('cdata-section-elements') and output.has_key('cdata-section-elements'):
		newvalues['cdata-section-elements'].update(output['cdata-section-elements'])
	
	# cdata-section-elements is already a union of old and new values
	output.update(newvalues)

	
def computeStringDefaultPriority(expr):
	# compute default priority [XSLT 5.5]
	# not used as of now
	AXIS_RE = r'(?:@?|?:(?:child|attribute)\:\:)'
	NODETYPE_RE = r'(?:comment|text|processing\-instruction|node)'
	NODETEST_RE = r'(?:'+NAMETEST_RE+r'|'+NODETYPE_RE+r'\(\)|processing-instruction([^"]*))'
	if re.match(AXIS_RE+r'(?:'+QNAME_RE+r'|processing-instruction([^"]*)$', self.match_s):
		self.priority = 0
	elif re.match(AXIS_RE+NCNAME_RE+r'\:\*$', self.match_s):
		self.priority = -0.25
	elif re.match(AXIS_RE+NODETEST_RE+r'$', self.match_s):
		self.priority = -0.5
	else:
		self.priority = 0.5
	
	
def computeDefaultPriority(pattern):
	"""Compute default priority [XSLT 5.5]. Accepts xpath.expr.Expr as pattern.
	Raises TypeError if pattern is UnionExpr."""
	
	import xpath.expr as X
	
	if type(pattern) is X.UnionExpr:
		raise TypeError
	
	# if the expressiong had a form of ChildOrAttributeAxisSpecifier NodeTest
	if type(pattern) is X.AbsolutePathExpr and \
			type(pattern.path) is X.PathExpr and \
			len(pattern.path.steps) == 2 and \
			type(pattern.path.steps[0]) is X.AxisStep and \
			type(pattern.path.steps[0].test) is X.AnyKindTest and \
			pattern.path.steps[0].axis.__name__ == 'descendant-or-self' and \
			type(pattern.path.steps[1]) is X.AxisStep:
		nodeTest = pattern.path.steps[1].test
		if type(nodeTest) is X.PITest: # processing-instruction(Literal)
			return 0
		if type(nodeTest) is X.NameTest:
			if nodeTest.localName != '*': # ChildOrAttributeAxisSpecifier QName
				return 0
			if nodeTest.prefix != '*' and nodeTest.localName == '*': # ChildOrAttributeAxisSpecifier NCName:*
				return -0.25
			return -0.5 # *
		return 0.5 # NodeTypeTest
	return 0.5
	
	
def splitUnionExpr(expr):
	"""Split a tree of UnionExpr's to a list of Expr's that are not UnionExpr"""
	
	import xpath.expr as X
	if type(expr) is X.UnionExpr:
		l = splitUnionExpr(expr.left)
		l += splitUnionExpr(expr.right)
		return l
	else:
		return [ expr ]
		

def mergeNameTestLists(dest, src, all=None):
	"""Adds items from src to dest if they are not in all.
	Returns dest."""
	
	if all is None:
		all = dest
	
	for test in src:
		if not isNameTestInList(test, all):
			dest.append(test)
			
	return dest