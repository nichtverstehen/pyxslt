import unittest
from xslt.tools import *
import xslt.exceptions, xslt.xp
import xml.dom.minidom
from StringIO import *

class TestIsWhitesSpaceNode(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.parseString('<x>   <z/>  b <z/> \t\r\n </x>')
		
	def testWhiteSpaceNode(self):
		r = isWhitespaceNode(self.doc.documentElement.childNodes[0])
		self.assertEqual(r, True)
	
	def testSpecial(self):
		r = isWhitespaceNode(self.doc.documentElement.childNodes[4])
		self.assertEqual(r, True)
		
	def testTextNode(self):
		r = isWhitespaceNode(self.doc.documentElement.childNodes[2])
		self.assertEqual(r, False)
		
	def testNotTextNode(self):
		r = isWhitespaceNode(self.doc.documentElement.childNodes[1])
		self.assertEqual(r, False)
		
class TestChildElements(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.parseString('<root>'+ \
			'<test><a/><a/></test>'+ \
			'<test>		</test>'+ \
			'<test><a/><b><c/></b></test>'+ \
			'<test>  <a> hi </a>  </test>'+ \
			'<test> hi <a/> </test>'+\
			'<test attr="not cause exception"></test>'+\
			'<test><?processing-instruction fail ?><f/></test></root>')
		self.root = self.doc.documentElement
			
	def testSimple(self):
		test = self.root.childNodes[0]
		r = childElements(test)
		self.assertEquals(len(r), 2)
		self.assertTrue(r[0] is test.childNodes[0])
		self.assertTrue(r[1] is test.childNodes[1])
		
	def testEmpty(self):
		test = self.root.childNodes[1]
		r = childElements(test)
		self.assertEquals(len(r), 0)
			
	def testNested(self):
		test = self.root.childNodes[2]
		r = childElements(test)
		self.assertEquals(len(r), 2)
		self.assertTrue(r[0] is test.childNodes[0])
		self.assertTrue(r[1] is test.childNodes[1])
			
	def testSkipWhitespace(self):
		test = self.root.childNodes[3]
		r = childElements(test)
		self.assertEquals(len(r), 1)
		self.assertTrue(r[0] is test.childNodes[1])
			
	def testFailText(self):
		test = self.root.childNodes[4]
		self.assertRaises(xslt.exceptions.UnexpectedNode, childElements, test)
			
	def testSkipAttr(self):
		test = self.root.childNodes[5]
		r = childElements(test)
		self.assertEquals(len(r), 0)
			
	def testFailPI(self):
		test = self.root.childNodes[6]
		self.assertRaises(xslt.exceptions.UnexpectedNode, childElements, test)
		
class TestIsNamespaceInList(unittest.TestCase):
	def testSimple(self):
		r = isNameTestInList(('a','b'), [('a','b')])
		self.assertEquals(r, True)
		r = isNameTestInList(('a','b'), [('a',None)])
		self.assertEquals(r, True)
		r = isNameTestInList(('a','b'), [(None,None)])
		self.assertEquals(r, True)
		r = isNameTestInList(('a','b'), [('a','c')])
		self.assertEquals(r, False)
		r = isNameTestInList(('a','b'), [('a','*')])
		self.assertEquals(r, False)
	def testNCNameWildcard(self):
		r = isNameTestInList(('a',None), [('a','b')])
		self.assertEquals(r, False)
		r = isNameTestInList(('a',None), [('a',None)])
		self.assertEquals(r, True)
		r = isNameTestInList(('a',None), [(None,None)])
		self.assertEquals(r, True)
		r = isNameTestInList(('a',None), [('a','c')])
		self.assertEquals(r, False)
		r = isNameTestInList(('a',None), [('a','*')])
		self.assertEquals(r, False)
	def testNCName(self):
		r = isNameTestInList((None,'b'), [('a','b')])
		self.assertEquals(r, False)
		r = isNameTestInList((None,'b'), [('b',None)])
		self.assertEquals(r, False)
		r = isNameTestInList((None,'b'), [(None,None)])
		self.assertEquals(r, True)
		r = isNameTestInList((None,'b'), [(None,'b')])
		self.assertEquals(r, True)
	def testWildcardWildcard(self):
		r = isNameTestInList((None,None), [('a','b')])
		self.assertEquals(r, False)
		r = isNameTestInList((None,None), [('a',None)])
		self.assertEquals(r, False)
		r = isNameTestInList((None,None), [(None,None)])
		self.assertEquals(r, True)
		r = isNameTestInList((None,None), [('a','c')])
		self.assertEquals(r, False)
		r = isNameTestInList((None,None), [('a','*')])
		self.assertEquals(r, False)
	def testList(self):
		r = isNameTestInList(('a','b'), [('a','b'), ('c',None)])
		self.assertEquals(r, True)
		r = isNameTestInList(('c','d'), [('a','b'), ('c',None)])
		self.assertEquals(r, True)
		
class TestStripSpace(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.parseString(
			'<a>'+\
			'<b xml:space="preserve"> <b xml:space="default"> </b> </b>'+\
			'<b> <u xmlns="uri:preserve"> <b> </b> </u> </b>'+\
			'</a>')
		self.root = self.doc.documentElement
		self.r = StringIO()
		
	def testXmlSpace(self):
		node = self.root.childNodes[0]
		stripSpace(node)
		node.writexml(self.r)
		self.assertEquals(self.r.getvalue(), '<b xml:space="preserve"> <b xml:space="default"/> </b>')
		
	def testOverrideXmlSpace(self):
		node = self.root.childNodes[0]
		stripSpace(node, stripSpaceList=[(None, 'b')])
		node.writexml(self.r)
		self.assertEquals(self.r.getvalue(), '<b xml:space="preserve"> <b xml:space="default"/> </b>')
	
	def testOverrideXmlSpace2(self):
		node = self.root.childNodes[0]
		stripSpace(node, preserveSpaceList=[(None, 'b')])
		node.writexml(self.r)
		self.assertEquals(self.r.getvalue(), '<b xml:space="preserve"> <b xml:space="default"> </b> </b>')
		
	def testNamespaces(self):
		node = self.root.childNodes[1]
		stripSpace(node, preserveSpaceList=[('uri:preserve', 'u')])
		node.writexml(self.r)
		self.assertEquals(self.r.getvalue(), '<b><u xmlns="uri:preserve"> <b/> </u></b>')
		
	def testDefaultStrip(self):
		node = self.root.childNodes[1]
		stripSpace(node, preserveSpaceList=[('uri:preserve', 'u')], defaultStrip=False)
		node.writexml(self.r)
		self.assertEquals(self.r.getvalue(), '<b> <u xmlns="uri:preserve"> <b/> </u> </b>')
		
class TestPushResult(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.getDOMImplementation().createDocument(None, None, None)
		
	def testPushToString(self):
		s = StringIO(); s.write(u"1")
		s = pushResult("2", s)
		self.assertEquals('12', s.getvalue())
		
		s = StringIO(); s.write(u"1")
		s = pushResult(u"я", s)
		self.assertEquals(u'1я', s.getvalue())
		
		s = StringIO(); s.write(u"1")
		t = self.doc.createTextNode(u"я")
		s = pushResult(t, s)
		self.assertEquals(s.getvalue(), u'1я')
		
		t = self.doc.createElement(u"a")
		self.assertRaises(xslt.exceptions.InvalidContent, pushResult, t, s)
		
	def testPushToCharacterData(self):
		t = self.doc.createTextNode("1")
		t = pushResult("2", t)
		self.assertEquals(t.data, '12')
		
		t = self.doc.createTextNode("1")
		t = pushResult(u"я", t)
		self.assertEquals(t.data, u'1я')
		
		t1 = self.doc.createElement(u"a")
		self.assertRaises(xslt.exceptions.InvalidContent, pushResult, t1, t)
		
	def testPushToAttribute(self):
		a = self.doc.createAttribute("n")
		a.value = "1"
		a = pushResult("2", a)
		self.assertEquals(a.value, '12')
		
		t1 = self.doc.createElement(u"a")
		self.assertRaises(xslt.exceptions.InvalidContent, pushResult, t1, a)
		
	def testPushToNode(self):
		root = self.doc.createElement('b')
		self.doc = pushResult(root, self.doc)
		self.assertEquals(self.doc.documentElement, root)
		
		a = xml.dom.minidom.getDOMImplementation().createDocument(None, None, None).createAttribute('hi')
		t = self.doc.createTextNode("1")
		a = pushResult(t, a)
		root = pushResult(a, root)
		
		s=StringIO()
		root.writexml(s)
		self.assertEquals(s.getvalue(), '<b hi="1"/>')
		
		root = pushResult( '2', root)
		s=StringIO()
		root.writexml(s)
		self.assertEquals(s.getvalue(), '<b hi="1">2</b>')
		
		root = pushResult(xml.dom.minidom.parseString('<a/>'), root)
		s=StringIO()
		root.writexml(s)
		self.assertEquals(s.getvalue(), '<b hi="1">2<a/></b>')
		
		a = self.doc.createAttribute('hi2')
		self.assertRaises(xslt.exceptions.UnexpectedAttribute, pushResult, a, root)
		
class TestSafeUpdateDict(unittest.TestCase):
	def testSimple(self):
		a = { 1: 1, 2: 2 }
		safeUpdateDict(a, { 1: 2, 3: 3 })
		self.assertEquals(a[1], 1)
		self.assertEquals(a[3], 3)
		
class TestCombineOutput(unittest.TestCase):
	def testSimple(self):
		a = { 'method': 'html' }
		combineOutput(a, { 'cdata-section-elements': set([(None, 'a')]) })
		self.assertEquals(a['cdata-section-elements'], set([(None, 'a')]))
		self.assertEquals(a['method'], 'html')
		
		combineOutput(a, { 'cdata-section-elements': set([('uri:test', 'b')]), 'method': 'xml', 'version': '1.0' })
		self.assertEquals(a['cdata-section-elements'], set([(None, 'a'), ('uri:test', 'b')]))
		self.assertEquals(a['method'], 'xml')
		self.assertEquals(a['version'], '1.0')
		
		combineOutput(a, { })
		self.assertEquals(a['cdata-section-elements'], set([(None, 'a'), ('uri:test', 'b')]))
		
class TestComputeDefaultPriority(unittest.TestCase):
	def testUnion(self):
		p = xslt.xp.Pattern('a|b|c[d|e]')
		self.assertRaises(TypeError, computeDefaultPriority, p.expr)
		
	def testQName(self):
		p = xslt.xp.Pattern('a:b')
		r = computeDefaultPriority(p.expr)
		self.assertEquals(r, 0)
		
	def testPI(self):
		p = xslt.xp.Pattern('processing-instruction(HUI)')
		r = computeDefaultPriority(p.expr)
		self.assertEquals(r, 0)
		
	def testNCNameWildcard(self):
		p = xslt.xp.Pattern('a:*')
		r = computeDefaultPriority(p.expr)
		self.assertEquals(r, -0.25)
		
	def testNodeTest(self):
		p = xslt.xp.Pattern('*')
		r = computeDefaultPriority(p.expr)
		self.assertEquals(r, -0.5)
		
	def testNodeTypeTest(self):
		p = xslt.xp.Pattern('node()')
		r = computeDefaultPriority(p.expr)
		self.assertEquals(r, 0.5)
		
	def testOtherwise(self):
		p = xslt.xp.Pattern('/a:b')
		r = computeDefaultPriority(p.expr)
		self.assertEquals(r, 0.5)
		
class TestSplitUnionExpr(unittest.TestCase):
	def testSimple(self):
		p = xslt.xp.Pattern('a|b|c[d|e]')
		e = p.expr
		l = splitUnionExpr(e)
		self.assertTrue(l[0] is e.left.left)
		self.assertTrue(l[1] is e.left.right)
		self.assertTrue(l[2] is e.right)
		
class TestGetNamespaceBindings(unittest.TestCase):
	def setUp(self):
		self.doc = xml.dom.minidom.parseString(
			'<a>'+\
			'<test xmlns:z="b"/>'+\
			'<test/>'+\
			'<test xmlns="a"/>'+\
			'</a>')
		self.root = self.doc.documentElement
		
	def testSimple(self):
		r = getNamespaceBindings(self.root.childNodes[0])
		self.assertEquals(r, {'z':'b'})
		
	def testEmpty(self):
		r = getNamespaceBindings(self.root.childNodes[1])
		self.assertEquals(r, {})
		
	def testDefault(self):
		r = getNamespaceBindings(self.root.childNodes[2])
		self.assertEquals(r, {None:'a'})
		
class TestMergeNameTestLists(unittest.TestCase):
	def testSimple(self):
		self.assertEquals([('a','b')], mergeNameTestLists([], [('a', 'b')], []))
		
	def testOverriding(self):
		self.assertEquals([], mergeNameTestLists([], [], [(None, None)]))
		self.assertEquals([], mergeNameTestLists([], [('a','b')], [(None, None)]))
		self.assertEquals([], mergeNameTestLists([], [('a',None)], [(None, None)]))
		self.assertEquals([], mergeNameTestLists([], [(None,None)], [(None, None)]))
		self.assertEquals([], mergeNameTestLists([], [('a','b')], [('a', None)]))
		self.assertEquals([('b', 'c')], mergeNameTestLists([], [('b','c')], [('a', None)]))
		self.assertEquals([], mergeNameTestLists([], [('a',None)], [('a', None)]))
		self.assertEquals([(None, None)], mergeNameTestLists([], [(None,None)], [('a', None)]))
		
if __name__ == '__main__':
    unittest.main()