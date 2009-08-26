import unittest
from xslt.properties import *
import xslt.exceptions
import xml.dom.minidom

class TestResolveNamespace(unittest.TestCase):

	def testSimple(self):
		self.assertEquals(resolveNamespace(None, {}, True), None)
		self.assertEquals(resolveNamespace(None, {None:'uri:test'}, True), 'uri:test')
		self.assertEquals(resolveNamespace(None, {None:'uri:test'}, False), None)
		self.assertEquals(resolveNamespace('a', {'a':'uri:test'}), 'uri:test')
		
		
class TestResolveQName(unittest.TestCase):
	# resolveNamespace and parseQName are also tested imlicitly

	def testNCName(self):
		uri, n = resolveQName('a')
		self.assertEquals((uri, n), (None, 'a'))
		
		
	def testResolveDefault(self):
		uri, n = resolveQName('a', namespaces={None:'uri:test'}, resolveDefault=True)
		self.assertEquals((uri, n), ('uri:test', 'a'))
		self.assertEquals(resolveQName('a', resolveDefault=True), (None, 'a'))
		
		
	def testQName(self):
		uri, n = resolveQName('z:a', namespaces={'z':'uri:test'})
		self.assertEquals((uri, n), ('uri:test', 'a'))
		self.assertRaises(xslt.exceptions.NamespaceNotFound, resolveQName, 'z:a')
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidName, resolveQName, '@a@')
		
		
class TestResolveNameTest(unittest.TestCase):

	def testWildcard(self):
		w = resolveNameTest('*')
		self.assertEquals(w, (None, None))
		
		
	def testNCName(self):
		w = resolveNameTest('a')
		self.assertEquals(w, (None, 'a'))
		
		
	def testResolveDefault(self):
		w = resolveNameTest('a', namespaces={None:'uri:test'}, resolveDefault=True)
		self.assertEquals(w, ('uri:test', 'a'))
		self.assertEquals(resolveNameTest('a', resolveDefault=True), (None, 'a'))
		
		
	def testQName(self):
		w = resolveNameTest('z:a', namespaces={'z':'uri:test'})
		self.assertEquals(w, ('uri:test', 'a'))
		self.assertRaises(xslt.exceptions.NamespaceNotFound, resolveNameTest, 'z:a')
		
		
	def testNCNameWildcard(self):
		w = resolveNameTest('z:*', namespaces={'z':'uri:test'})
		self.assertEquals(w, ('uri:test', None))
		self.assertRaises(xslt.exceptions.NamespaceNotFound, resolveNameTest, 'z:*')
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidName, resolveNameTest, '@a@')
		
class TestProperties(unittest.TestCase):

	def setUp(self):
		self.doc = xml.dom.minidom.parseString('''<root
			str="a"
			float="5.3"
			bool1="yes"
			bool2="no"
			qname="h:b"
			ncname="b"
			qnameList="a b h:b"
			nametestList="a h:* *"
			nsList="#default h"
			nsPrefix1="h"
			nsPrefix2="#default"
			expr="1.0"
			pattern="a"
		></root>''')
		self.root = self.doc.documentElement

		
class TestStringProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(stringProperty(self.root, 'str'), 'a')
		
		
	def testRequired(self):
		self.assertRaises(xslt.exceptions.AttributeRequired, stringProperty, self.root, 'str1', required=True)
		
		
	def testAbsent(self):
		self.assertEquals(stringProperty(self.root, 'str1'), None)
		self.assertEquals(stringProperty(self.root, 'str1', default='z'), 'z')
		
		
class TestFloatProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(floatProperty(self.root, 'float'), 5.3)

		
	def testAbsent(self):
		self.assertEquals(floatProperty(self.root, 'float1'), None)
		self.assertEquals(floatProperty(self.root, 'float1', default=1.1), 1.1)
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidAttribute, floatProperty, self.root, 'str')
		
		
class TestBoolProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(boolProperty(self.root, 'bool1'), True)
		self.assertEquals(boolProperty(self.root, 'bool2'), False)

		
	def testAbsent(self):
		self.assertEquals(boolProperty(self.root, 'bool0'), False)
		self.assertEquals(boolProperty(self.root, 'bool0', default=True), True)
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidAttribute, boolProperty, self.root, 'str')
		
		
class TestQNameProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(qnameProperty(self.root, 'qname', namespaces={'h':'uri:test'}), ('uri:test', 'b'))

		
	def testAbsent(self):
		self.assertEquals(qnameProperty(self.root, 'qname0'), None)
		self.assertEquals(qnameProperty(self.root, 'qname0', default='b'), (None, 'b'))
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidAttribute, qnameProperty, self.root, 'float')
		self.assertRaises(xslt.exceptions.NamespaceNotFound, qnameProperty, self.root, 'qname')
		
		
class TestQNameListProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(qnameListProperty(self.root, 'qnameList', namespaces={'h':'uri:test'}), 
			[(None,'a'),(None,'b'),('uri:test', 'b')])

		
	def testAbsent(self):
		self.assertEquals(qnameListProperty(self.root, 'qname0'), None)
		self.assertEquals(qnameListProperty(self.root, 'qname0', default=' a '), [(None, 'a')])
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidAttribute, qnameListProperty, self.root, 'float')
		self.assertRaises(xslt.exceptions.NamespaceNotFound, qnameListProperty, self.root, 'qnameList')
		
		
class TestNameTestListProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(nameTestListProperty(self.root, 'nametestList', namespaces={'h':'uri:test'}), 
			[(None,'a'),('uri:test', None), (None, None)])

		
	def testAbsent(self):
		self.assertEquals(nameTestListProperty(self.root, 'nametestList0'), None)
		self.assertEquals(nameTestListProperty(self.root, 'nametestList0', default=' a '), [(None, 'a')])
		
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidAttribute, nameTestListProperty, self.root, 'float')
		self.assertRaises(xslt.exceptions.NamespaceNotFound, nameTestListProperty, self.root, 'nametestList')
		
		
class TestNSPrefixProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(nsPrefixProperty(self.root, 'nsPrefix1', namespaces={'h':'uri:test'}), 'uri:test')
		self.assertEquals(nsPrefixProperty(self.root, 'nsPrefix2', namespaces={None:'uri:test'}), 'uri:test')

		
	def testAbsent(self):
		self.assertEquals(nsPrefixProperty(self.root, 'nsPrefix0'), None)
		self.assertEquals(nsPrefixProperty(self.root, 'nsPrefix0', default='h', namespaces={'h':'uri:test'}), 'uri:test')
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.NamespaceNotFound, nsPrefixProperty, self.root, 'nsPrefix1')
		self.assertRaises(xslt.exceptions.NamespaceNotFound, nsPrefixProperty, self.root, 'nsPrefix0', default='h')
		
		
class TestNSListProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(nsListProperty(self.root, 'nsList', namespaces={'h':'uri:test', None:'uri:test1'}), ['uri:test1', 'uri:test'])

		
	def testAbsent(self):
		self.assertEquals(nsListProperty(self.root, 'nsList0'), None)
		self.assertEquals(nsListProperty(self.root, 'nsList0', default='h', namespaces={'h':'uri:test'}), ['uri:test'])
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.NamespaceNotFound, nsListProperty, self.root, 'nsList')
		
		
class TestExprProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(str(exprProperty(self.root, 'expr')), '1.0')

		
	def testAbsent(self):
		self.assertEquals(exprProperty(self.root, 'expr0'), None)
		self.assertEquals(str(exprProperty(self.root, 'expr0', default='*')), 'child::*:*')
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidAttribute, exprProperty, self.root, 'nsPrefix2')
		
		
class TestPatternProperty(TestProperties):

	def testSimple(self):
		self.assertEquals(str(patternProperty(self.root, 'pattern')), '/descendant-or-self::node()/child::a')

		
	def testAbsent(self):
		self.assertEquals(patternProperty(self.root, 'pattern0'), None)
		self.assertEquals(str(patternProperty(self.root, 'pattern0', default='*')), '/descendant-or-self::node()/child::*:*')
		
		
	def testInvalid(self):
		self.assertRaises(xslt.exceptions.InvalidAttribute, patternProperty, self.root, 'nsPrefix2')
		
		
if __name__ == '__main__':
    unittest.main()