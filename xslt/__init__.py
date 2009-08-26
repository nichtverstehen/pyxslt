# elements need to register themselves as Element subclasses
import core
import elements

from stylesheet import Stylesheet
from exceptions import *


class XSLTProcessor(object):
	def __init__(self, dp=core.DocumentProvider()):
		self.dp = dp
		self.stylesheet = None
		self.params = {}
		
	def setStylesheet(self, uriOrDoc):
		self.stylesheet = Stylesheet(uriOrDoc, dp=self.dp)
		
	def setParameter(self, name, value=None):
		if value is None:
			del self.params[name]
		else:
			self.params[name] = value
			
	def createContext(self):
		context = core.XSLTContext(self.stylesheet)
		context.params = self.params.copy()
		return context
		
	def transformToDoc(self, uriOrDoc):
		context = self.createContext()
		return self.stylesheet.transformToDoc(uriOrDoc, context)
		
	def transform(self, uriOrDoc, messages=None):
		context = self.createContext()
		
		s = self.stylesheet.transformToString(uriOrDoc, context)
		
		if messages is not None:
			messages.extend(context.messages)
			
		return s
	