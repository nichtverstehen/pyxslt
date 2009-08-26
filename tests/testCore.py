import unittest
from xslt.core import *
import xslt.exceptions, xslt.xp
import xml.dom.minidom
from StringIO import *

class TestAssertEmptyNode(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.parseString('<x><y></y><y a="b"></y><y> </y></x>')
		self.root = self.doc.documentElement
	def testSimple(self):
		self.assertEqual(None, assertEmptyNode(self.root.childNodes[0]), "empty element")
		self.assertEqual(None, assertEmptyNode(self.root.childNodes[1]))
		self.assertRaises(xslt.exceptions.UnexpectedNode, assertEmptyNode, self.root.childNodes[2])
		
class TestXsltChildren(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.parseString('<root xmlns:s="http://www.w3.org/1999/XSL/Transform">'+ \
			'<test> <s:a/>\r\n<s:b/>\t</test>'+ \
			'<test> <s:a/><s:b/><c/></test>'+ \
			'<test xmlns="http://www.w3.org/1999/XSL/Transform"><a/><i:b xmlns:i="http://www.w3.org/1999/XSL/Transform"><c/></i:b></test>'+ \
			'</root>')
		self.root = self.doc.documentElement
			
	def testSkipWhitespace(self):
		test = self.root.childNodes[0]
		r = xsltChildren(test, ['a', 'b'])
		self.assertEquals(len(r), 2)
		self.assertTrue(r[0] is test.childNodes[1])
		self.assertTrue(r[1] is test.childNodes[3])
		
	def testAllowedNames(self):
		test = self.root.childNodes[0]
		self.assertRaises(xslt.exceptions.UnexpectedNode, xsltChildren, test, ['a'])
		
	def testFailElement(self):
		test = self.root.childNodes[1]
		self.assertRaises(xslt.exceptions.UnexpectedNode, xsltChildren, test, ['a', 'b'])
		
	def testXmlns(self):
		test = self.root.childNodes[2]
		r = xsltChildren(test, ['a', 'b'])
		self.assertEquals(len(r), 2)
		self.assertTrue(r[0] is test.childNodes[0])
		self.assertTrue(r[1] is test.childNodes[1])
		
class TestXsltHeader(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.parseString('<root xmlns:s="http://www.w3.org/1999/XSL/Transform">'+ \
			'<test> <s:a/>\r\n<s:b/>\t</test>'+ \
			'<test> <s:a/><s:b/><c/></test>'+ \
			'<test xmlns="http://www.w3.org/1999/XSL/Transform"><a/><i:b xmlns:i="http://www.w3.org/1999/XSL/Transform"><c/></i:b></test>'+ \
			'<test></test>'+\
			'</root>')
		self.root = self.doc.documentElement
		
	def testEmpty(self):
		test = self.root.childNodes[3]
		r,t = xsltHeader(test, ['a'])
		self.assertEquals(len(r), 0)
		self.assertEquals(len(t), 0)
			
	def testSkipWhitespace(self):
		test = self.root.childNodes[0]
		r, t = xsltHeader(test, ['a', 'b'])
		self.assertEquals(len(r), 2)
		self.assertTrue(r[0] is test.childNodes[1])
		self.assertTrue(r[1] is test.childNodes[3])
		self.assertEquals(t, [test.childNodes[0], test.childNodes[2], test.childNodes[4]])
		
	def testAllowedNames(self):
		test = self.root.childNodes[0]
		r, t = xsltHeader(test, ['a'])
		self.assertEquals(len(r), 1)
		self.assertTrue(r[0] is test.childNodes[1])
		self.assertEquals(t, [test.childNodes[0], test.childNodes[2], test.childNodes[3], test.childNodes[4]])
		
	def testFailElement(self):
		test = self.root.childNodes[1]
		r, t = xsltHeader(test, ['a', 'b'])
		self.assertEquals(len(r), 2)
		self.assertTrue(r[0] is test.childNodes[1])
		self.assertTrue(r[1] is test.childNodes[2])
		self.assertEquals(t, [test.childNodes[0], test.childNodes[3]])
	
	
class TestTemplateContent(unittest.TestCase):

	def testInit(self):
		class TemplateContentMockAddNodes(TemplateContent):
			def __init__(self, *args, **kwargs):
				self.addNodesRun = None
				super(TemplateContentMockAddNodes, self).__init__(*args, **kwargs)
			def addNodes(self, *args, **kwargs):
				self.addNodesRun = args
				
		z1 = TemplateContentMockAddNodes()
		self.assertEquals(z1.addNodesRun, None)
		z2 = TemplateContentMockAddNodes([1],2,3)
		self.assertEquals(z2.addNodesRun, ([1],2,3))
		
	def createMockedTC(self, expectedSS, expectedO):
		class ElementFactoryMock(object):
			def new(self, name, element, stylesheet, options):
				return name
			def newE(self, element, stylesheet, options):
				if stylesheet != expectedSS:
					raise "Stylesheet error"
				if options != expectedO:
					raise "Options error"
				return '<%s>' % element.tagName
		z = TemplateContent()
		z._ef = ElementFactoryMock()
		return z
		
	def testAddNodes(self):
		doc = xml.dom.minidom.parseString('<z xmlns:xsl="http://www.w3.org/1999/XSL/Transform">'+
			'<xsl:copy/> text <xsl:value-of/><e/><xsl:hui/><xsl:stylesheet/></z>')
		root = doc.documentElement
		
		options = {'extensionElementsNS':[], 'forwardsCompatible': False}
		tc = self.createMockedTC(1, options)
		tc.addNodes(root.childNodes[0:4], 1, options)
		self.assertEquals(tc.children, ['<xsl:copy>', '_literal_text', '<xsl:value-of>', '_literal_element'])
		
		tc = self.createMockedTC(1, options)
		self.assertRaises(xslt.exceptions.NotImplemented, tc.addNodes, root.childNodes[4:5], 1, options)
		
		tc = self.createMockedTC(1, options)
		self.assertRaises(xslt.exceptions.NotImplemented, tc.addNodes, root.childNodes[5:], 1, options)
		
	def createMockedContext(self, name):
		class ContextMock(object):
			def __init__(self, name):
				self.name = name
				self.result = '@'
			def __str__(self):
				return name+':'+self.result
			def copy(self):
				return ContextMock(name+'copy')
		return ContextMock(name)
		
	def createMockedElement(self):
		class ElementMock(object):
			def instantiate(self, context):
				self.inst = str(context)
		return ElementMock()
	
	def testInstantiate(self):
		z = TemplateContent()
		a = [self.createMockedElement() for i in range(2)]
		z.children = a[:]
		z.instantiate(self.createMockedContext('ctx'))
		self.assertEquals(map(lambda x: x.inst, a), ['ctx:@', 'ctx:@'])
		
	def testInstantiateTo(self):
		z = TemplateContent()
		a = [self.createMockedElement() for i in range(2)]
		z.children = a[:]
		z.instantiateTo(self.createMockedContext('ctx'), 'to')
		self.assertEquals(map(lambda x: x.inst, a), ['ctx:to', 'ctx:to'])


class ElementTest(unittest.TestCase):
	class ElementMock(Element):
		def __init__(self, test):
			self._test = args[3]
			z=xml.dom.minidom.parseString('<a xmlns="A" xmlns:b="B"/>').documentElement.firstChild
			o = { 'namespaces': {1:2, None:3} }
			Element.__init__(self, z, )
			self._test.assertEquals(args[1], self.stylesheet)
			self._test.assertEquals(args[1], self.stylesheet)
		def initImpl(self, *args):
			if self.initImplCall is not None:
				self._test.fail("initImpl called twice")
			self._test.assertEquals(args[0:2], self._args[0:2])
		def instantiateImpl(self, context):
			if self.instImplCall is not None:
				self._test.fail("instImplCall called twice")
			
#	def testElement

if __name__ == '__main__':
    unittest.main()