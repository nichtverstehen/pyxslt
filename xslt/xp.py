import xpath.expr, xpath.parser
import xpath.yappsrt, xpath.exceptions
import tools
		
		
class XPathBase(object):
	_max_cache = 100
	_cache = {}

	def __init__(self, expr, useCache=True):
		"""Init docs.
		"""
		
		if isinstance(expr, xpath.expr.Expr):
			self.expr = expr
			return
			
		if useCache:
			self.expr = type(self).get(expr)
		else:
			self.expr = type(self).compile(expr)

	@classmethod
	def get(cls, s):
		if isinstance(s, xpath.expr.Expr):
			return s
		
		if s not in cls._cache:
			if len(cls._cache) >= cls._max_cache:
				del cls._cache[0:cls._max_cache/2]
				
			cls._cache[s] = cls.compile(s)
			
		return cls._cache[s]
	
	@staticmethod
	def compile(s):
		try:
			parser = xpath.parser.XPath(xpath.parser.XPathScanner(str(s)))
			expr = parser.XPath()
		except xpath.yappsrt.SyntaxError, e:
			raise xpath.exceptions.XPathParseError(str(s), e.pos, e.msg)
		return expr

	@xpath.api
	def find(self, context):
		return self.expr.evaluate(context.node, context.pos, context.size, context)

	def __repr__(self):
		return '%s.%s(%s)' % (type(self).__module__,
								type(self).__name__,
								repr(str(self.expr)))

	def __str__(self):
		return str(self.expr)

class XPath(XPathBase):
	_max_cache = 100
	_cache = {}
	
	@xpath.api
	def findNodeset(self, context):
		result = self.find(context)
		if not xpath.expr.nodesetp(result):
			raise XPathTypeError("expression is not a node-set")
		return result

	@xpath.api
	def findNode(self, context):
		result = self.findnodeset(context)
		if len(result) == 0:
			return None
		return result[0]

	@xpath.api
	def findBoolean(self, context):
		result = self.find(context)
		return xpath.tools.boolean(result, context)

	@xpath.api
	def findString(self, context):
		result = self.find(context)
		return xpath.tools.string(result, context)

	@xpath.api
	def findNumber(self, context):
		result = self.find(node, context, **kwargs)
		return xpath.tools.number(result, context)

class Pattern(XPathBase):
	_max_cache = 100
	_cache = {}
	
	@staticmethod
	def compile(s):
		try:
			parser = xpath.parser.XPath(xpath.parser.XPathScanner(str(s)))
			expr = parser.Pattern()
		except xpath.yappsrt.SyntaxError, e:
			raise xpath.exceptions.XPathParseError(str(s), e.pos, e.msg)
		return expr
		
	@xpath.api
	def nodes(self, context):
		result = self.find(context)
		if not xpath.expr.nodesetp(result):
			raise XPathTypeError("expression is not a node-set")
		return result
		
class AttributeTemplate(XPathBase):
	_max_cache = 100
	_cache = {}
	
	@staticmethod
	def compile(s):
		try:
			parser = xpath.parser.XPath(xpath.parser.XPathScanner(str(s)))
			expr = parser.AttributeValueTemplate()
		except xpath.yappsrt.SyntaxError, e:
			raise xpath.exceptions.XPathParseError(str(s), e.pos, e.msg)
		return expr
		
	@xpath.api
	def value(self, context):
		result = self.find(context)
		if xpath.expr.nodesetp(result):
			if len(result) == 0:
				return None
		result = xpath.tools.string(result, context)
		return result
		
		