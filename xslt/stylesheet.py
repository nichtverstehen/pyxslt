from xml.dom import Node
import core
import properties
import xp
import elements
import serializer
from exceptions import *
from tools import *


class Stylesheet(object):

	def __init__(self, uriOrDoc=None, dp=core.DocumentProvider()):
		self.dp = dp
		
		if isinstance(uriOrDoc, xml.dom.Node):
			if uriOrDoc.nodeType != xml.dom.Node.DOCUMENT_NODE:
				uriOrDoc = uriOrDoc.ownerDocument
			uriOrDoc = self.dp.addDOMDocument(doc)
			
		doc = self.dp.document(uriOrDoc)

		self.stripSpace = []
		self.preserveSpace = []
		self.output = {}
		self.keys = {}
		self.decimalFormats = {}
		self.attrSets = {}
		self.namespaceAliases = {}
		
		self.variables = {}
		self.templates = [] # not used
		self.patterns = { (None, None): [] }
		self.namedTemplates = {}
		self.imports = []
		
		self._parseStylesheetContent(doc, uriOrDoc)
		for i in self.patterns:
			self.patterns[i].sort(key=lambda x: x[2])
		
		self.imports.reverse()
		for imp in self.imports: # descending import precedence
			safeUpdateDict(self.variables, imp.variables)
			safeUpdateDict(self.namespaceAliases, imp.namespaceAliases)
			mergeNameTestLists(self.stripSpace, imp.stripSpace, self.stripSpace+self.preserveSpace)
			mergeNameTestLists(self.preserveSpace, imp.preserveSpace, self.stripSpace+self.preserveSpace)
			combineOutput(self.output, imp.output)
			for key in imp.keys.values():
				self.addKey(key)
		
	def transform(self, uriOrDoc, context):
		if isinstance(uriOrDoc, xml.dom.Node):
			if uriOrDoc.nodeType != xml.dom.Node.DOCUMENT_NODE:
				uriOrDoc = uriOrDoc.ownerDocument
			uriOrDoc = self.dp.addDOMDocument(doc)
			
		doc = self.dp.document(uriOrDoc)
		
		stripSpace(doc, self.stripSpace, self.preserveSpace, defaultStrip=False)
		
		result = self.dp.createDocument().createDocumentFragment()
		context.nodeset = [doc]
		context.result = result
		
		for i, v in self.variables.iteritems():
			v.instantiate(context)

		self.applyTemplates(context, (None, None))
		
		return result
		
		
	def transformToDoc(self, *args):
		frag = self.transform(*args)
		doc = frag.ownerDocument
		doc.appendChild(frag)
		core.fixNamespaces(doc)
		return doc
		
		
	def transformToString(self, *args):
		frag = self.transform(*args)
		core.fixNamespaces(frag)
		
		method = self.output.get('method', (None, 'xml'))
		if method == (None, 'xml'):
			ser = serializer.XMLSerializer(self.output)
		elif method == (None, 'text'):
			ser = serializer.TextSerializer(self.output)
			
		if ser is not None:
			return ser.serializeResult(frag)
		else:
			return ''
		
		
	def _parseStylesheetContent(self, doc, baseUri):
		sheet = doc.documentElement
		if sheet.namespaceURI != core.XSLT_NAMESPACE or not(sheet.localName == 'stylesheet' or sheet.localName == 'transform'):
			raise UnexpectedNode(doc.documentElement)
		
		# compile options (that are specified as xsl:stylesheet attributes) are valid only within this stylesheet 
		# (not include and imports) [XSLT 7.1.1], [XSLT 14.1]
		options = {}
		options['forwardsCompatible'] = sheet.getAttribute('version') != '1.0'
		options['namespaces'] = getNamespaceBindings(sheet)
		options['extensionElementsNS'] = properties.nsListProperty(sheet, 
				'extension-element-prefixes', namespaces=options['namespaces']) or []
		options['excludeResultNS'] = properties.nsListProperty(sheet, 
				'exclude-result-prefixes', namespaces=options['namespaces']) or []
		options['baseUri'] = baseUri
		options['definedVars'] = []
		stripSpace(sheet, preserveSpaceList=[(core.XSLT_NAMESPACE, 'text')])
		
		for i in range(sheet.childNodes.length):
			node = sheet.childNodes.item(i)
			if node.nodeType != Node.ELEMENT_NODE:
				continue
			
			if node.namespaceURI != core.XSLT_NAMESPACE: # Ignore top-level elements with an unknown non-null namespace [XSLT 2.2] 
				if node.namespaceURI == None: 
					raise UnexpectedNode(doc.documentElement.tagName)
				continue
				
			if node.localName == 'import':
				# TODO: check that imports come first
				href = properties.stringProperty(node, 'href', required=True)
				self.imports.append(Stylesheet(href, dp=self.dp))
				
			if node.localName == 'include':
				href = properties.stringProperty(node, 'href', required=True)
				self._parseStylesheetContent(self.dp.document(href, baseUri), self.dp.absUri(href, baseUri))
				
			if node.localName == 'variable' or node.localName == 'param':
				varclass = elements.Param if node.localName == 'param' else elements.Variable
				var = varclass(node, self, options)
				self.variables[var.name] = var
				
			if node.localName == 'template':
				template = elements.Template(node, self, options)
				self.addTemplateRule(template)
				
			if node.localName == 'strip-space':
				space = elements.SpaceStripping(node)
				self.stripSpace.extend(space.nameTests())
				
			if node.localName == 'preserve-space':
				space = elements.SpaceStripping(node)
				self.preserveSpace.extend(space.nameTests())
				
			if node.localName == 'output':
				output = elements.Output(node, self, options)
				combineOutput(self.output, output.outputDict())
					
			if node.localName == 'key':
				key = elements.Key(node, self, options)
				self.addKey(key)
				
			if node.localName == 'decimal-format':
				raise NotImplemented(node.localName)
				
			if node.localName == 'namespace-alias':
				alias = elements.NamespaceAlias(node, self, options)
				ss, res = alias.getTuple()
				# accept one that occurs last
				self.namespaceAliases[ss] = res
				
			if node.localName == 'attribute-set':
				aset = AttributeSet(node, self, options)
				if aset.name in self.attrSets: self.attrSets[aset.name].update(aset)
				else: self.attrSets[aset.name] = aset
				
				
	def addKey(self, key):
		if self.keys.has_key(key.name):
			self.keys[key.name].update(key)
		else:
			self.keys[key.name] = key
	
	
	def instantiateAttributeSet(self, context, name):
		"""Instantiate attribute set by name.
		Attributte-sets from imported stylesheets are applyed"""
		
		for imp in self.imports:
			imp.instantiateAttributeSet(context, name)
		
		attrSet = self.attrSets.get(name)
		if attrSet:
			attrSet.instantiate(context)
			
	
	def getNamespaceAlias(self, uri):
		"""Try to remap namespaceURI using defined alises.
		If no alias is specified for a URI just return passes URI."""
		
		return self.namespaceAliases.get(uri, uri)
	
	
	def addTemplateRule(self, template):
		self.templates.append(template)
		
		if template.name is not None:
			if template.name in self.namedTemplates:
				raise DuplicateName
			name = template.name
			self.namedTemplates[name] = template
			
		elif template.patterns is not None:
			patterns = template.patterns
			mode = template.mode
			if not self.patterns.has_key(mode):
				self.patterns[mode] = []
			self.patterns[mode] += patterns
				
				
	def initMode(self, context, mode):
		self._matchAll(context, mode)
		for i in self.imports:
			i.initMode(context, mode)
		
		
	def _matchAll(self, context, mode):
		document = (context.node.ownerDocument
				if context.node.nodeType != Node.DOCUMENT_NODE
				else context.node)
				
		handle = (hash(self), hash(document), mode)
		
		if handle in context.matches:
			return # already matched this stylesheet agains current document and current mode
		
		patterns = self.patterns[mode]
		matches = {}
		nsCopy = context.namespaces.copy()
		for (pattern, template, priority) in patterns:
			context.namespaces.update(template.namespaces)
			nodes = template.match.nodes(context)
			for node in nodes:
				matches[hash(node)] = template
				
		context.matches[handle] = matches
	
	
	def applyTemplates(self, context, mode):
		for node in context:
			self.applyTemplatesImpl(context, mode)
			
			
	def applyImports(self, context):
		if context.cause == (None, None):
			return # top-level element or for-each
			
		for i in self.imports:
			if context.cause[0] == None:
				r = i.applyTemplatesImpl(context, context.cause[1])
			else:
				r = i.callTemplate(context, context.cause[0])
				
			if r:
				return True
			
			
	def applyTemplatesImpl(self, context, mode):
		self.initMode(context, mode)
		
		context.cause = (None, mode)
		node = context.node
		doc = (context.node.ownerDocument
				if context.node.nodeType != Node.DOCUMENT_NODE
				else context.node)
		handle = (hash(self), hash(doc), mode)
		if hash(node) in context.matches[handle]:
			context.matches[handle][hash(node)].instantiate(context)
			return True
		else:
			r = self.applyImports(context)
			if r:
				return True
		
		if self != context.stylesheet: # non top-level stylesheet
			return False
			
		# else built-ins in top-level
		if context.node.nodeType == Node.ELEMENT_NODE or \
				context.node.nodeType == Node.DOCUMENT_NODE:
			if node.childNodes.length > 0:
				subContext = context.copy()
				subContext.nodeset = list(node.childNodes)
				self.applyTemplates(subContext, mode)
		elif context.node.nodeType == Node.TEXT_NODE or \
				context.node.nodeType == Node.CDATA_SECTION_NODE or \
				node.nodeType == Node.ATTRIBUTE_NODE:
			context.pushResult(context.node)
		# OK: <xsl:template match="processing-instruction()|comment()"/>
		# OK: The built-in template rule for namespace nodes is also to do nothing
			
			
	def callTemplate(self, context, name):
		context.cause = (name, None)
		if name in self.namedTemplates:
			self.namedTemplates[name].instantiate(context)
			return True
		else:
			self.applyImports(context)
			if self != context.stylesheet: # non top-level
				return False
				
			raise NamedTemplateNotFound
