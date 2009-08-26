import tools, properties
import xp
from StringIO import StringIO
from properties import *
from core import *

		
class LiteralText(Element):
	"""Compatible with Element to be an XSLT tree node.
	Represents a text from the stylesheet that needs just to be copied to result tree."""
	
	name = '_literal_text'
	
	def __init__(self, node, stylesheet, options):
		self.text = node.data
	
	
	def instantiate(self, context):
		context.pushResult(self.text)
		
		
class LiteralElement(Element):
	name = '_literal_element'
	
	def initImpl(self, element, stylesheet, options):
		self.name = (element.prefix, element.localName)
		self.ns = element.namespaceURI
		self.useSets = qnameListProperty(element, (XSLT_NAMESPACE, 'use-attribute-sets'),
				namespaces=options['namespaces'], default='', resolveDefault=False)
				
		options['excludeResultNS'].extend(properties.nsListProperty(element, 
				(XSLT_NAMESPACE, 'exclude-result-prefixes'), namespaces=options['namespaces']) or [])
		options['extensionElementsNS'].extend(properties.nsListProperty(element, 
				'extension-element-prefixes', namespaces=options['namespaces']) or [])
		if (stringProperty(element, (XSLT_NAMESPACE, 'version'), default='1.0') != '1.0'):
			options['forwardsCompatible'] = True
		if (stringProperty(element, (XSLT_NAMESPACE, 'version')) == '1.0'):
			options['forwardsCompatible'] = False
		
		self.attrs = {}
		for i in range(element.attributes.length):
			attr = element.attributes.item(i)
			
			if attr.namespaceURI == XSLT_NAMESPACE:
				# do not copy xsl: attributes
				continue
			
			if attr.namespaceURI == xml.dom.XMLNS_NAMESPACE:
				# check if this namespace node is excluded
				localName = attr.localName if attr.localName != 'xmlns' else None
				nsUri = resolveNamespace(localName, options['namespaces'], resolveDefault=True)
				if nsUri in options['excludeResultNS']:
					continue
			
			self.attrs[(attr.prefix, attr.localName, attr.namespaceURI)] = xp.AttributeTemplate(attr.value)
			
		self.setContent(element.childNodes, stylesheet, options)
			
			
	def instantiateImpl(self, context):
		ss = context.stylesheet
		e = context.resultDocument.createElementNS(ss.getNamespaceAlias(self.ns), tools.formatQName(self.name))
		
		for attrSet in self.useSets:
			ss.instantiateAttributeSet(context, attrSet)
			
		for (k, v) in self.attrs.iteritems():
			if k[2] == xml.dom.XMLNS_NAMESPACE:
				e.setAttributeNS(k[2], 'xmlns:%s'%k[1], ss.getNamespaceAlias(v.value(context)))
			else:
				e.setAttributeNS(ss.getNamespaceAlias(k[2]), tools.formatQName(k[0:2]), v.value(context))
				
		context.pushResult(e)
		context.result = e
		self.instantiateContent(context)
		
		
class PerformFallback(Element):
	name = '_perform_fallback'
	
	def initImpl(self, element, stylesheet, options):
		fallbacks = filter(lambda x: x.namespaceURI == XSLT_NAMESPACE and x.localName == 'fallback', 
							childElements(element))
		self.setContent(fallbacks, stylesheet, options)
			
	def instantiateImpl(self, context):
		context.fallback = True
		self.instantiateContent(context)
		
		
class Output(Element):
	name = 'output'	
	
	
	def initImpl(self, node, stylesheet, options):
		output = {}
		
		if node.hasAttribute('method'): 
			output['method'] = qnameProperty(node, 'method', \
				namespaces=options['namespaces'], resolveDefault=False)
		if node.hasAttribute('indent'): 
			output['indent'] = boolsProperty(node, 'indent')
		if node.hasAttribute('encoding'): 
			output['encoding'] = stringProperty(node, 'encoding')
		if node.hasAttribute('version'): 
			output['version'] = stringProperty(node, 'version')
		if node.hasAttribute('standalone'): 
			output['standalone'] = boolProperty(node, 'standalone')
		if node.hasAttribute('omit-xml-declaration'): 
			output['omit-xml-declaration'] = boolProperty(node, 'omit-xml-declaration')
		if node.hasAttribute('doctype-system'): 
			output['doctype-system'] = stringProperty(node, 'doctype-system')
		if node.hasAttribute('doctype-public'): 
			output['doctype-public'] = stringProperty(node, 'doctype-public')
		if node.hasAttribute('cdata-section-elements'): 
			output['cdata-section-elements'] = set(qnameListProperty(node, \
				'cdata-section-elements', namespaces=options['namespaces'], resolveDefault=True))
		if node.hasAttribute('media-type'): 
			output['media-type'] = stringProperty(node, 'media-type')
			
		self.output = output
		
		assertEmptyNode(node)
		
		
	def outputDict(self):
		return self.output
		
		
class SpaceStripping(Element):

	def initImpl(self, element, stylesheet, options):
		self.nametests = nameTestListProperty(element, 'elements', \
			namespaces=options['namespaces'], resolveDefault=True, required=True)
		assertEmptyNode(element)
		
	def nameTests(self):
		return self.nametests


class NamespaceAlias(Element):
	name = 'namespace-alias'
	
	
	def initImpl(self, element, stylesheet, options):
		stylesheetUri = nsPrefixProperty(element, 'stylesheet-prefix', \
			namespaces=options['namespaces'], required=True)
		resultUri = nsPrefixProperty(element, 'result-prefix', \
			namespaces=options['namespaces'], required=True)
		self.t = (stylesheetUri, resultUri)
		assertEmptyNode(element)
		
		
	def getTuple(self):
		return self.t
		
		
class AttributeSet(Element):
	name = 'attribute-set'
	
	
	def initImpl(self, node, stylesheet, options):
		self.name = qnameProperty(node, 'name', required=True,
				namespaces=options['namespaces'], resolveDefault=False)
		self.useSets = qnameListProperty(node, 'use-attribute-sets',
				namespaces=options['namespaces'], default='', resolveDefault=False)
		attrs = xsltChildren(node, allowedNames='attribute')
		self.attributes = dict((attr.name, attr) for attr in attrs)
		
		
	def update(self, attrSet):
		"""Add attribute definitions from attrSet, 
		replacing existing attributes."""
		
		self.attributes.update(attrSet.attributes)
		self.useSets += attrset.useSets
		
		
	def instantiateImpl(self, context):
		context.variables = context.toplevelContext.variables.copy()
		
		for attrSet in self.useSets:
			context.stylesheet.instantiateAttributeSet(context, attrSet)
			
		for a in self.attributes:
			a.instantiate(context)
			
			
class Key(Element):
	name = 'Key'
	
	
	def initImpl(self, node, stylesheet, options):
		self.name = qnameProperty(node, 'name', required=True,
				namespaces=options['namespaces'], resolveDefault=False)
		match = patternProperty(node, 'match', required=True)
		use = exprProperty(node, 'user', required=True)
		self.keys = (match, use)
		
		
	def update(self, key):
		self.keys.extend(key.keys)
		
		
	def select(self, context, value):
		subContext = context.toplevelContext.copy()
		nodes = []
		for key in self.keys:
			cands = key[0].nodes(subContext)
			for cand in cands:
				subContext.nodeset = [cand]
				if key[1].findString(subContext) == xpath.tools.string(value, context):
					nodes.append(cand)
		
		return nodes
		
		
class Template(Element):
	name = 'template'
	
	
	def initImpl(self, element, stylesheet, options):
		self.mode = qnameProperty(element, 'mode') or (None, None)
		self.name = qnameProperty(element, 'name')
		self.match = patternProperty(element, 'match')
		self.priority = floatProperty(element, 'priority')
		
		self.patterns = None
		if self.match != None:
			# split union pattern and  compute priority for each one
			patterns = tools.splitUnionExpr(self.match.expr)
			self.patterns = [ ( xp.Pattern(p), self, 
								tools.computeDefaultPriority(p) if self.priority is None else self.priority )
								for p in patterns ]
						 
		params, content = xsltHeader(element, allowedNames=['param'])
		options['definedVars'] = []
		self.params = [Param(i, stylesheet, options) for i in params]
		self.setContent(content, stylesheet, options)
		
		
	def instantiateImpl(self, context):
		context.variables = context.toplevelContext.variables.copy()
		
		for param in self.params:
			param.instantiate(context)
			
		self.instantiateContent(context)
		
		
class Variable(Element):
	name = 'variable'
	
	
	def initImpl(self, element, stylesheet, options):
		self.name = qnameProperty(element, 'name', namespaces=options['namespaces'], required=True)
		self.select = exprProperty(element, 'select')
		self.addDefinition(options)
		
		if self.select is not None:
			assertEmptyNode(element)
		else:
			self.setContent(element.childNodes, stylesheet, options)
		
		
	def addDefinition(self, options):
		if self.name in options['definedVars']:
			raise VariableRedefinition(self.name)
		options['definedVars'].append(self.name)
		
		
	def instantiateImpl(self, context):
		if self.select:
			context.parent.variables[self.name] = self.select.find(context)
		else:
			varTree = context.resultDocument.createDocumentFragment()
			varTree.xslt_baseUri = self.baseUri
			context.parent.variables[self.name] = varTree
			context.result = varTree
			self.instantiateContent(context)
			
		
class Param(Variable):
	name = 'param'
	
	def instantiateImpl(self, context):
		if self.name in context.params:
			context.parent.variables[self.name] = context.params[self.name]
		else:
			super(Param, self).instantiateImpl(context)
			
			
class WithParam(Element):
	name = 'with-param'
	
	def initImpl(self, element, stylesheet, options):
		self.name = qnameProperty(element, 'name', namespaces=options['namespaces'], required=True)
		self.select = exprProperty(element, 'select')
		
		if self.select is not None:
			assertEmptyNode(element)
		else:
			self.setContent(element.childNodes, stylesheet, options)
		
		
	def instantiateImpl(self, context):
		if self.select is not None:
			context.params[self.name] = self.select.find(context)
		else:
			varTree = context.resultDocument.createDocumentFragment()
			varTree.xslt_baseUri = self.baseUri
			context.params[self.name] = varTree
			context.result = varTree
			self.instantiateContent(context)
		
		
class Sort(object):
	name = 'sort'
	
	def __init__(self, element, stylesheet, options):
		self.select = exprProperty(element, 'select', default='.')
		self.lang = stringProperty(element, 'lang')
		self.dataType = stringProperty(element, 'data-type', default='text', choises=['text', 'number'])
		
		order = stringProperty(element, 'order', defauld='ascending', choices=['ascending', 'descending'])
		self.asc = order == 'ascending'
		
		caseOrder = stringProperty(element, 'case-order', default='upper-first', choices=['upper-first', 'lower-first'])
		self.upperFirst = caseOrder == 'upper-first'
	
	
	def compare(context, node1, node2):
		subContext = context.copy()
		
		subContext.nodeset = [node1]
		v1 = self.select.find(subContext)
		subContext.nodeset = [node2]
		v2 = self.select.find(subContext)
		
		if self.dataType == (None, 'text'):
			v1 = xpath.expr.string(v1)
			v2 = xpath.expr.string(v2)
		if self.dataType == (None, 'number'):
			v1 = xpath.expr.number(v1)
			v2 = xpath.expr.number(v2)
			
		r = cmp(v1, v2)
		if not self.asc:
			r = -r
		return r
	
	
	@staticmethod
	def sort(context, sortList):
		def compare(a, b):
			for sort in sortList:
				r = sort.compare(context, a, b)
				if r != 0:
					return r
		if sortList:
			context.nodeset.sort(compare)
		
class ApplyTemplates(Element):
	name = 'apply-templates'
	
	def initImpl(self, element, stylesheet, options):
		self.select = exprProperty(element, 'select', default='node()')
		self.mode = qnameProperty(element, 'mode', namespaces=options['namespaces']) or (None, None)
		
		self.params = []
		self.sorts = []
		children = xsltChildren(element, allowedNames=['with-param', 'sort'])
		for i in children:
			if i.localName == 'sort':
				self.sorts.append(Sort(i, stylesheet, options))
			if i.localName == 'with-param':
				self.params.append(WithParam(i, stylesheet, options))
		
		
	def instantiateImpl(self, context):
		context.nodeset = self.select.findNodeset(context)
		Sort.sort(context, self.sorts)
		context.params = {}
		for i in self.params:
			i.instantiate(context)
		context.stylesheet.applyTemplates(context, self.mode)
			
			
class CallTemplate(Element):
	name = 'call-template'
	
	def initImpl(self, element, stylesheet, options):
		self.name = qnameProperty(element, 'name', namespaces=options['namespaces'], required=True)
		children = xsltChildren(element, allowedNames=['with-param'])
		self.params = [WithParam(i, stylesheet, options) for i in children]
		
	def instantiateImpl(self, context):
		context.params = {}
		for i in self.params:
			i.instantiate(context)
		context.stylesheet.callTemplate(context, self.name)

		
class ForEach(Element):
	name = 'for-each'
	
	def initImpl(self, element, stylesheet, options):
		self.select = exprProperty(element, 'select', required=True)
		sorts, content = xsltHeader(element, allowedNames=['sort'])
		self.sorts = [Sort(i, stylesheet, options) for i in sorts]
		self.setContent(content, stylesheet, options)
			
	def instantiateImpl(self, context):
		context.nodeset = self.select.findNodeset(context)
		context.cause = (None, None)
		Sort.sort(context, self.sorts)
		for node in context:
			self.instantiateContent(context)
			
	
class Comment(Element):
	name = 'comment'
	
	def initImpl(self, element, stylesheet, options):
		self.setContent(element.childNodes, stylesheet, options)
		
	def instantiateImpl(self, context):
		comment = resultDocument.createComment(text)
		context.pushResult(comment)
		context.result = comment
		self.instantiateContent(context)
		
		
class Copy(Element):
	name = 'copy'
	
	def initImpl(self, element, stylesheet, options):
		self.useSets = qnameListProperty(element, 'use-attribute-sets',
				namespaces=options['namespaces'], default='', resolveDefault=False)
		self.setContent(element.childNodes, stylesheet, options)
	
	
	def instantiateImpl(self, context):
		r = context.resultDocument.importNode(context.node, False)
		if r.nodeType == xml.dom.Node.ELEMENT_NODE:
			# don't copy attrs except xmlns
			for i in reversed(range(r.attributes.length)):
				attr = r.attributes.item(i)
				if attr.namespaceURI == xml.dom.XMLNS_NAMESPACE:
					if attr.value in options['excludeResultNS']:
						r.removeAttributeNode(attr)
				if attr.namespaceURI != xml.dom.XMLNS_NAMESPACE:
					r.removeAttributeNode(attr)
					
		context.pushResult(r)
		context.result = r
		
		for s in useSets:
			context.stylesheet.instantiateAttributeSet(context, s)
			
			
class CopyOf(Element):
	name = 'copy-of'
	
	def initImpl(self, element, stylesheet, options):
		self.select = exprProperty(element, 'select', required=True)
		assertEmptyNode(element)
	
	
	def instantiateImpl(self, context):
		value = self.select.find(context)
		
		if not xpath.expr.nodesetp(value):
			value = xpath.expr.string(value)
			
		context.pushResult(value)
		
		
class ValueOf(Element):
	name = 'value-of'
	
	def initImpl(self, element, stylesheet, options):
		self.select = exprProperty(element, 'select', required=True)
		self.disableOutputExcaping = boolProperty(element, 'disable-output-escaping')
		
		
	def instantiateImpl(self, context):
		value = self.select.findString(context)
		text = context.resultDocument.createTextNode(value)
		text.xslt_disableOutputExcaping = self.disableOutputExcaping
		context.pushResult(text)
		
		
class ApplyImports(Element):
	name = 'apply-imports'
	
	def initImpl(self, element, stylesheet, options):
		assertEmptyNode(element)
		
	def instantiateImpl(self, context):
		context.stylesheet.applyImports(context)
		
		
class Number(Element):
	name = 'number'
	def initImpl(self, element, stylesheet, options):
		pass
	def instantiateImpl(self, context):
		pass
		
class Choose(Element):
	name = 'choose'
	
	def initImpl(self, element, stylesheet, options):
		whens, tail = xsltHeader(element, ['when'])
		
		otherwise = xsltChildren(tail, ['otherwise'])
		if len(otherwise) == 0: otherwise = None
		elif len(otherwise) == 1: otherwise = otherwise[0]
		else: raise UnexpecedNode(otherwise[1])
			
		self.whens = [When(when, stylesheet, options) for when in whens]
		if otherwise:
			self.otherwise = TemplateContent(otherwise.childNodes, stylesheet, options)
		
	def instantiateImpl(self, context):
		for when in self.whens:
			if when.test(context):
				when.instantiate(context)
				return
		
		if self.otherwise:
			self.otherwise.instantiate(context)
		
		
class When(Element):
	name = 'when'
		
	def initImpl(self, element, stylesheet, options):
		self.testExpr = exprProperty(element, 'test', required=True)
		self.setContent(element.childNodes, stylesheet, options)
		
	def test(self, context):
		return self.testExpr.findBoolean(context)
		
	def instantiateImpl(self, context):
		self.instantiateContent(context)
		
		
class If(Element):
	name = 'if'
	
	def initImpl(self, element, stylesheet, options):
		self.test = exprProperty(element, 'test', required=True)
		self.setContent(element.childNodes, stylesheet, options)
		
	def instantiateImpl(self, context):
		r = self.test.findBoolean(context)
		if r:
			self.instantiateContent(context)
			
			
class Text(Element):
	name = 'text'
	
	def initImpl(self, element, stylesheet, options):
		self.disableOutputExcaping = boolProperty(element, 'disable-output-escaping')
		self.setContent(element.childNodes, stylesheet, options)
		
	def instantiateImpl(self, context):
		r = context.resultDocument.createTextNode('')
		r.xslt_disableOutputExcaping = self.disableOutputExcaping
		context.pushResult(r)
		context.result = r
		self.instantiateContent(context)
		
		
class Message(Element):
	name = 'message'
	
	def initImpl(self, element, stylesheet, options):
		self.terminate = boolProperty(element, 'terminate', default=False)
		self.setContent(element.childNodes, stylesheet, options)
		
	def instantiateImpl(self, context):
		context.result = StringIO()
		self.instantiateContent(context)
		context.toplevelContext.messages.append(context.result.getvalue())
		if self.terminate:
			raise Terminate(context.result.getvalue())
		
		
class Fallback(Element):
	name = 'fallback'
	
	def initImpl(self, element, stylesheet, options):
		self.setContent(element.childNodes, stylesheet, options)
		
	def instantiateImpl(self, context):
		if context.fallback:
			self.instantiateContent(context)
		
		
class ProcessingInstruction(Element):
	name = 'processing-instruction'
	
	def initImpl(self, element, stylesheet, options):
		self.name = stringProperty(element, 'name')
		self.setContent(element.childNodes, stylesheet, options)
		# TODO: check name is NCName and PITarget
		
		
	def instantiateImpl(self, context):
		context.result = StringIO()
		self.instantiateContent(context)
		pi = context.resultDocument.createProcessingInstruction(self.name.value(context), context.result.getvalue())
		context.pushResult(pi)
		
class ElementTemplate(Element):
	name = 'element'
	
	def initImpl(self, element, stylesheet, options):
		self.name = attributeTemplateProperty(element, 'name', required=True)
		self.namespace = attributeTemplateProperty(element, 'namespace')
		self.useSets = qnameListProperty(element, 'use-attribute-sets',
				namespaces=options['namespaces'], default='', resolveDefault=False)
		self.setContent(element.childNodes, stylesheet, options)
		
  
	def instantiateImpl(self, context):
		name = parseQName(self.name.value(context))
		if namespace is None:
			namespace = resolveQName(name, namespaces=context.namespaces, resolveDefault=True)[0]
		else:
			namespace = self.namespace.value(context)
			if namespace == '':
				namespace = None

		e = context.resultDocument.createElementNS(namespace, formatQName(name))
		context.pushResult(e)
		context.result = e
		
		for attrSet in self.useSets: 
			context.stylesheet.instantiateAttributeSet(context, attrSet)
			
		self.instantiateContent(context)
		
class Attribute(Element):
	name = 'attribute'
	def initImpl(self, element, stylesheet, options):
		self.name = attributeTemplateProperty(element, 'name', required=True)
		self.namespace = attributeTemplateProperty(element, 'namespace')
		self.setContent(element.childNodes, stylesheet, options)
		
	def instantiateImpl(self, context):
		name = parseQName(self.name.value(context))
		if namespace is None:
			namespace = resolveQName(name, namespaces=context.namespaces, resolveDefault=True)[0]
		else:
			namespace = self.namespace.value(context)
			if namespace == '':
				namespace = None
		
		e = context.resultDocument.createAttribute(namespace, formatQName(name))
		context.pushResult(e)
		context.result = e
		self.instantiateContent(context)
		