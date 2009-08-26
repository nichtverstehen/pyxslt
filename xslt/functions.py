from xpath.functions import function
import xpath.tools
import properties
import core
import xml.dom

@function(0, 0)
def f_current(node, pos, size, context):
	return [node]
	
@function(0, 1, implicit=True, first=True)
def f_generate_id(node, pos, size, context, v):
	if v is None:
		return ''
	return u'id'+hash(v)
	
@function(1, 1, convert='string')
def f_system_property(node, pos, size, context, s):
	qn = properties.resolveQName(s, namespaces=context.namespaces)
	if qn == (core.XSLT_NAMESPACE, 'version'):
		return u'1.0'
	elif qn == (core.XSLT_NAMESPACE, 'vendor'):
		return u'Cyril Nikolaev'
	elif qn == (core.XSLT_NAMESPACE, 'vendor'):
		return u'mailto:cyril7@gmail.com'
	else:
		return ''
		
@function(1, 1, convert='string')
def f_unparsed_entity_uri(node, pos, size, context, s):
	return ''
	
@function(0, 1, implicit=True)
def f_string(node, pos, size, context, v):
	if (isinstance(v, xml.dom.Node) and
			v.nodeType == xml.dom.Node.DOCUMENT_FRAGMENT_NODE):
		return xpath.tools.string_value(v)
	else:
		return xpath.functions.f_string(node, pos, size, context, v)
		
@function(0, 1, implicit=True)
def f_number(node, pos, size, context, v):
	if (isinstance(v, xml.dom.Node) and
			v.nodeType == xml.dom.Node.DOCUMENT_FRAGMENT_NODE):
		v = xpath.tools.string(v, context)
	return xpath.functions.f_number(node, pos, size, context, v)

@function(0, 1, implicit=True)
def f_boolean(node, pos, size, context, v):
	if (isinstance(v, xml.dom.Node) and
			v.nodeType == xml.dom.Node.DOCUMENT_FRAGMENT_NODE):
		v = xpath.tools.string(v, context)
	return xpath.functions.f_boolean(node, pos, size, context, v)

	
@function(1, 2)
def f_document(node, pos, size, context, obj, nodeset = None): 
	if xpath.tools.nodesetp(obj):
		r = []
		for x in obj:
			r += f_document(node, pos, size, context, 
				xpath.tools.string(x, context), 
				nodeset or [x])
		return r
				
	if nodeset is None:
		baseUri = context.baseUri
	else:
		if xpath.tools.nodesetp(nodeset):
			baseUri = (nodeset[0].ownerDocument.baseUri 
						if nodeset[0].nodeType != xml.dom.Node.DOCUMENT_NODE 
						else nodeset[0].baseUri)
		elif (isinstance(nodeset, xml.dom.Node) and
				nodeset.nodeType == xml.dom.Node.DOCUMENT_FRAGMENT):
			baseUri = nodeset.baseUri
		else:
			baseUri = '' # wow!?
			
	uri = xpath.tools.string(object, context)
	return [context.stylesheet.dp.document(uri, baseUri)]
	

@function(1, 1, convert='string')
def f_element_available(node, pos, size, context, name):
	name = properties.resolveQName(name, namespaces=context.namespaces)
	if name[0] == None:
		name = name[1]
		
	return name in core.Element.classDict
	
@function(1, 1, convert='string')
def f_function_available(node, pos, size, context, name):
	name = properties.resolveQName(name, namespaces=context.namespaces)
	if name[0] == None:
		name = name[1]
	
	return name in context.functions
	
	
@function(2, 2)
def f_key(node, pos, size, context, name, obj):
	name = xpath.tools.string(name, context)
	
	if xpath.tools.nodesetp(obj):
		r = []
		for x in obj:
			r += f_key(node, pos, size, context, name, x)
		return r
		
	name = properties.resolveQName(name, namespaces=context.namespaces)
	return context.stylesheet.keys[name].select(context, obj)
	