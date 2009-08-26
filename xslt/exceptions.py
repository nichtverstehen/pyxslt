class XSLTError(Exception):
	pass
	
class CompileError(XSLTError):
	pass
	
class RuntimeError(XSLTError):
	pass
	
class UnexpectedNode(CompileError):
	"""Raised when a forbidden element is met in XSLT document."""
	
	def __init__(self, node):
		self.node = node
		
	def __unicode__(self):
		return u"UnexpectedNode(%s)" % self.node.nodeName
	
class InvalidContent(RuntimeError):
	"""Raised when a template tried to and invalid or unexpected 
	content to result document."""
	
	def __init__(self, content):
		self.content = content
		
	def __unicode__(self):
		return u"%s(%s)" % (type(self).__name__, unicode(self.content))
	
class UnexpectedAttribute(RuntimeError):
	"""Raised if an attribute is generated after some content 
	was generated."""
	pass
	
class InvalidName(CompileError):
	"""Raised if an name (QName or NameTest) is malformed."""
	
	def __init__(self, name):
		self.name = name
		
	def __unicode__(self):
		return u'NamespaceNotFound(%s)' % (self.name)
		
class VariableRedefinition(CompileError):
	"""Raised if a variable name is already used."""
	
	def __init__(self, name):
		self.name = name
		
	def __unicode__(self):
		return u'VariableRedefinition(%s)' % (self.name)
	
class NamespaceNotFound(CompileError):
	"""Raised when the processor cannot resolve namespace prefix."""
	
	def __init__(self, prefix, name):
		self.prefix = prefix
		self.name = name
		
	def __unicode__(self):
		return u'NamespaceNotFound(%s, %s)' % (self.prefix, self.name)
		
class AttributeRequired(CompileError):
	"""Raised when an element in XSLT document lacks a required attribute."""
	
	def __init__(self, el, prop):
		self.element = el.nodeName
		self.prop = prop
		
	def __unicode__(self):
		return u'AttributeRequired(%s, %s)' % (self.element, self.prop)
		
class InvalidAttribute(CompileError):
	"""Raised when an attribute values is not acceptable."""
	
	def __init__(self, el, prop, value, cause = None):
		self.element = el.nodeName
		self.prop = prop
		self.value = value
		self.cause = cause
		
	def __unicode__(self):
		s = u'AttributeRequired(%s, %s, %s)' % (self.element, self.prop, self.value)
		if self.cause:
			s += '\n\t'
			s += str(self.cause)
		return s
		
class Recursion(RuntimeError):
	"""Raised when an attribute values is not acceptable."""
	
	def __init__(self, type, name):
		self.type = type
		self.name = name
		
	def __unicode__(self):
		return u'Recursion(%s, %s)' % (self.type, self.name)
		
		
class NotFound(RuntimeError):
	"""Raised when some name reference (like named attribute set)
	is not found."""
	
	def __init__(self, type, name):
		self.type = type
		self.name = name
		
	def __unicode__(self):
		return u'NotFound(%s, %s)' % (self.type, self.name)
		
		
class Terminate(RuntimeError):
	"""Raised when xsl:message caused terminate."""
	
	def __init__(self, message):
		self.msg = message
		
	def __unicode__(self):
		return u'Terminate(%s)' % (self.msg)
	
	
class NotImplemented(CompileError):
	pass
	