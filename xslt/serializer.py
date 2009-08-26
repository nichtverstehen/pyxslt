from StringIO import StringIO
import xml.dom
from xml.sax.saxutils import quoteattr, escape

class XMLSerializer(object):
	def __init__(self, output):
		self.output = output
		
	def serializeResult(self, frag):
		s = StringIO()
		
		if self.output.get('omit-xml-declaration') != True:
			s.write('<?xml')
			s.write(' version="%s"' % self.output.get('version', '1.0'))
			if self.output.has_key('encoding'):
				s.write(' encoding="%s"' % self.output.get('encoding'))
			if self.output.has_key('standalone'):
				s.write(' standalone="%s"' % ('yes' if self.output.get('standalone') else 'no'))
			s.write('?>')
			
		if self.output.has_key('doctype-system'):
			s.write('<!DOCTYPE %s' % frag.firstChild.nodeName)
			if self.output.has_key('doctype-public'):
				s.write(' PUBLIC %s %s' % (self.output.get('doctype-public'), self.output.get('doctype-system')))
			else:
				s.write(' SYSTEM %s' % self.output.get('doctype-system'))
			s.write('>')
			
		self.serialize(frag, s)
		
		return s.getvalue().encode(self.output.get('encoding', 'utf-8'))
			
	def serializeDoc(self, doc):
		pass
		
	def serialize(self, node, writer, indent=0):
		if node.nodeType == xml.dom.Node.ATTRIBUTE_NODE:
			writer.write(' %s=%s' % (node.name, quoteattr(node.value)))
			
		elif node.nodeType == xml.dom.Node.CDATA_SECTION_NODE:
			s = node.data.replace(']]>', ']]]]><![CDATA[>')
			writer.write('<![CDATA[%s]]>' % s)
			
		elif node.nodeType == xml.dom.Node.COMMENT_NODE:
			s = node.data.replace('--', '- -')
			if s[-1:] == '-': s += ' '
			writer.write('<!--%s-->' % s)
			
		elif node.nodeType in (xml.dom.Node.DOCUMENT_FRAGMENT_NODE, 
				xml.dom.Node.DOCUMENT_NODE):
			for i in node.childNodes:
				self.serialize(i, writer, indent)
				
		elif node.nodeType == xml.dom.Node.ELEMENT_NODE:
			if self.output.get('indent', False):
				writer.write( '\n' + '  ' * indent)
			writer.write('<%s' % node.tagName)
			for i in range(node.attributes.length):
				attr = node.attributes.item(i)
				self.serialize(attr, writer, indent)
			
			if node.childNodes.length > 0:
				writer.write('>')
				
				for i in node.childNodes:
					self.serialize(i, writer, indent+1)
				
				if self.output.get('indent', False):
					writer.write( '\n' + '  ' * indent)
					
				writer.write('</%s>' % node.tagName)
			else:
				writer.write('/>')
			
		elif node.nodeType == xml.dom.Node.ENTITY_REFERENCE_NODE:
			writer.write('&%s;' % node.nodeName)
			
		elif node.nodeType == xml.dom.Node.PROCESSING_INSTRUCTION_NODE:
			writer.write('<?%s %s?>' % (node.nodeName, node.nodeValue))
			
		elif node.nodeType == xml.dom.Node.TEXT_NODE:
			if (node.parentNode is not None and 
					(node.parentNode.namespaceURI, node.parentNode.localName) in 
					self.output.get('cdata-section-elements', set())):
				s = node.data.replace(']]>', ']]]]><![CDATA[>')
				writer.write('<![CDATA[%s]]>' % s)
			else:
				s = node.data
				
				if (hasattr(node, 'xslt_disableOutputExcaping') and 
						getattr(node, 'xslt_disableOutputExcaping')):
					s = escape(s)
					
				writer.write(s)
				
class TextSerializer(object):
	def __init__(self, output):
		self.output = output
		
	def serializeResult(self, frag):
		s = StringIO()
		self.serialize(frag, s)
		return s.getvalue().encode(self.output.get('encoding', 'utf-8'))
		
	def serialize(self, node, writer, indent=0):
		if node.nodeType in (xml.dom.Node.DOCUMENT_FRAGMENT_NODE, 
				xml.dom.Node.DOCUMENT_NODE, xml.dom.Node.ELEMENT_NODE):
			for i in node.childNodes:
				self.serialize(i, writer)
				
		elif node.nodeType == xml.dom.Node.TEXT_NODE:
			writer.write(node.data)
				