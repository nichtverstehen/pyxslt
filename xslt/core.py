import tools
import xp, xslt.functions
import os.path, sys
import xml.dom.minidom
from properties import *

XSLT_NAMESPACE = 'http://www.w3.org/1999/XSL/Transform'

def xsltHeader(node, allowedNames=[]):
	"""xsltHeader iterates over nodes' children and stores 
	all children from XSLT namespace with allowedNames in elements list
	until it sees any disallowed node (that is not whitespace).
	Skipped whitespace nodes with any remainder of child nodes
	is called tail. xsltHeader returns a tuple (elements, tail)."""
	
	elements = []
	tail = []
		
	i = 0
	for i in range(node.childNodes.length):
		child = node.childNodes.item(i)
		if tools.isWhitespaceNode(child):
			tail.append(child)
				
		elif child.nodeType == xml.dom.Node.ELEMENT_NODE and \
				child.namespaceURI == XSLT_NAMESPACE and \
				child.localName in allowedNames:
			elements.append(child)
			
		else:
			tail.append(child)
			break
				
	for i in range(i+1, node.childNodes.length):
		tail.append(node.childNodes.item(i))
		
	return (elements, tail)
	
	
def xsltChildren(node, allowedNames=[]):
	"""Returns a list of all node's child elements
	from XSLT namespace with localName in allowedNames.
	If the node has any other child nodes that are node whitespace
	it raises UnexpectedNode"""
	
	if isinstance(node, list):
		children = node
	else:
		children = node.childNodes
		
	elements = []
	for child in children:
		if tools.isWhitespaceNode(child):
			pass #ignore
		elif child.nodeType == xml.dom.Node.ELEMENT_NODE and \
				child.namespaceURI == XSLT_NAMESPACE and \
				child.localName in allowedNames:
			elements.append(child)
		else:
			raise UnexpectedNode(i)
			
	return elements
	
def fixNamespaces(node):
	"""Add missing namespace definitions (xmlns: attributes)
	for namespace URI's used in node subtree"""
	
	if node.nodeType == xml.dom.Node.ELEMENT_NODE:
		ns = tools.getNamespaceBindings(node)
		if node.namespaceURI not in ns.values():
			node.setAttributeNS(xml.dom.XMLNS_NAMESPACE, 'xmlns:'+node.prefix, node.namespaceURI)
		for i in range(node.attributes.length):
			attr = node.attributes.item(i)
			if attr.namespaceURI not in ns.values() and attr.namespaceURI != xml.dom.XMLNS_NAMESPACE:
				node.setAttributeNS(xml.dom.XMLNS_NAMESPACE, 'xmlns:'+attr.prefix, attr.namespaceURI)
	else:
		for i in node.childNodes:
			fixNamespaces(i)
	
def assertEmptyNode(node):
	"""Raises an UnexpectedNode excpetion if node has children"""
	
	if node.childNodes.length > 0:
		raise UnexpectedNode(node.firstChild)
		
		
class DocumentProvider(object):
	def __init__(self):
		self.cache = {}
	
	def document(self, uri, base = ''):
		uri = self.absUri(uri, base)
		
		if uri not in self.cache:
			self.cache[uri] = xml.dom.minidom.parse(uri)
			self.cache[uri].baseUri = uri
			
		return self.cache[uri]
		
	def addDOMDocument(self, doc):
		uri = '#id'+hash(doc)
		self.cache[uri] = doc
		doc.baseUri = uri
		return uri
		
	def absUri(self, uri, base = ''):
		if uri == '':
			return base
			
		base = os.path.abspath(os.path.dirname(base))
		uri = os.path.join(base, uri)
		return uri
		
	def createDocument(self):
		return xml.dom.getDOMImplementation().createDocument(None, None, None)
		
		
class XSLTContext(object):
	"""XSLT stylesheet execution context.
	Compatible with xpath.XPathContext."""
	
	functions = xpath.functions.xpath_functions
	functions.update(xslt.functions.xpath_functions)
	
	def __init__(self, stylesheet, parent=None):
		# stylesheet applyed (root of import tree)
		self._stylesheet = stylesheet
		self._parent = parent
		
		# for attr-sets and apply-imports
		self.toplevelContext = self
		
		self.matches = {}
		self.messages = []
		self.fallback = False
		
		# template calling info
		self.cause = (None, None)
		self.params = {}
		
		self.baseUri = ''
		self.namespaces = {}
		self.variables = {}
		self._pos = 0
		self._nodeSet = [None]
		
		self.result = None
		
	@property
	def stylesheet(self):
		return self._stylesheet
		
	@property
	def parent(self):
		return self._parent
		
	def copy(self):
		ctx = type(self)(self.stylesheet, self)
		ctx.__dict__.update(self.__dict__)
		ctx._parent = self
		ctx.variables = self.variables.copy()
		return ctx
	
	def __iter__(self):
		for self._pos in range(self.size):
			yield self.node
		
	@property
	def resultDocument(self):
		return self.result.ownerDocument
		
	@property
	def nodeset(self):
		return self._nodeSet
	
	@nodeset.setter
	def nodeset(self, newList):
		self._nodeSet = newList
		self._pos = 0
		
	@property
	def node(self):
		return self.nodeset[self._pos]
		
	@property
	def size(self):
		return len(self.nodeset)
		
	@property
	def pos(self):
		return self._pos
		
	def pushResult(self, value):
		tools.pushResult(value, self.result)
		return value
		

class TemplateContent(object):
	"""Creates a list XSLT Elements from a list of DOM nodes
	to instantiate them in context.
	It is the main way to create Element objects."""

	allowedElements = [ 'apply-templates', 'call-template', 'apply-imports',
		'for-each', 'value-of', 'copy-of', 'number', 'choose', 'if', 'text',
		'copy', 'variable', 'message', 'fallback' ]

	def __init__(self, nodeList=None, stylesheet=None, options=None):
		"""If nodeList is not None initializes children list with Elements
		created from nodeList."""
		
		# allow to inject other ElementFactory
		self._ef = ElementFactory()
		self.children = []
		
		if nodeList is not None:
			self.addNodes(nodeList, stylesheet, options)
			
			
	def addNodes(self, nodeList, stylesheet, options):
		"""Adds Element objects created from nodes in the nodeList"""
		for templateNode in nodeList:
			if templateNode.nodeType == xml.dom.Node.ELEMENT_NODE:
				if templateNode.namespaceURI == XSLT_NAMESPACE:
					if templateNode.localName in TemplateContent.allowedElements:
						e = self._ef.newE(templateNode, stylesheet, options)
					else:
						if options['forwardsCompatible']:
							e = self._ef.new('_perform_fallback', templateNode, stylesheet, options)
						else:
							raise NotImplemented # TODO: forwards-compatible
				else:
					if templateNode.namespaceURI in options['extensionElementsNS']:
						try:
							e = self._ef.new((templateNode.namespaceURI, templateNode.localName), 
									templateNode, stylesheet, options)
						except UnexpectedNode:
							if options['forwardsCompatible']:
								e = self._ef.new('_perform_fallback', templateNode, stylesheet, options)
							else:
								raise
					else:
						e = self._ef.new('_literal_element', templateNode, stylesheet, options)
			elif templateNode.nodeType == xml.dom.Node.TEXT_NODE:
				e = self._ef.new('_literal_text', templateNode, stylesheet, options)
				
			self.children.append(e)
		
		
	def instantiate(self, context):
		"""Instantiate all children to context sequentially."""
		
		for child in self.children:
			child.instantiate(context)
			
			
class ElementFactory(object):
	def new(self, name, element, stylesheet, options):
		"""Creates an object of approprite Element subclass for an name"""
		
		try:
			subcls = Element.classDict[name]
		except KeyError:
			raise UnexpectedNode(element)
			
		return subcls(element, stylesheet, options)
		
	def newE(self, element, stylesheet, options):
		"""Creates an object of approprite Element subclass for an element node"""
		
		return self.new(element.localName, element, stylesheet, options)
		
		
class Element(object):
	"""Base class for all XSLT Elements. Element implementors
	should override initImpl and instantiateImpl"""
	
	__metaclass__ = tools.ClassInitializer
	@staticmethod
	def _init_class(cls, name, bases, dict):
		if dict.get('name') is not None: cls.classDict[dict.get('name')] = cls
	classDict = {}
		
	def __init__(self, element, stylesheet, options):
		self.stylesheet = stylesheet
		self.baseUri = options['baseUri']
		self.content = None
		
		subOptions = options.copy()
		subOptions['namespaces'] = subOptions['namespaces'].copy()
		subOptions['namespaces'].update(tools.getNamespaceBindings(element))
		self.namespaces = subOptions['namespaces']
		
		children = self.initImpl(element, stylesheet, subOptions)
			

	def setContent(self, children, stylesheet, options):
		"""Compiles children nodes and saves as content.
		Usually called by subclasses in initImpl."""
		
		self.content = TemplateContent(children, stylesheet, options)
		
	def initImpl(self, element, stylesheet, options):
		"""Override in subclass to examine an element node 
		and context in which it occurs in XSLT document.
		options['namespaces'] includes all effective namespace bindings."""
		
		pass
		
		
	def instantiateContent(self, context):	
		"""Used by subclasses to instantiate contents compiled by setContent."""
		
		if self.content:
			self.content.instantiate(context)
		
	
	def instantiate(self, context):
		subContext = context.copy()
		subContext.namespaces = self.namespaces
		subContext.baseUri =  self.baseUri
		r = self.instantiateImpl(subContext)
		
	def instantiateImpl(self, context):
		"""Override in subclass to control what 
		will be output to result."""
		
		pass
		
		
