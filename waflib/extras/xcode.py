#! /usr/bin/env python
# encoding: utf-8
# XCode 3/XCode 4 generator for Waf
# Nicolas Mercier 2011
# Modified by Simon Warg 2015
# XCode project file format based on http://www.monobjc.net/xcode-project-file-format.html

"""
Usage:

def options(opt):
	opt.load('xcode')

$ waf configure xcode
"""

# TODO: support iOS projects

from waflib import Context, TaskGen, Build, Utils, ConfigSet, Configure, Errors
import os, sys, random, time

HEADERS_GLOB = '**/(*.h|*.hpp|*.H|*.inl)'

MAP_EXT = {
	'.h' :  "sourcecode.c.h",

	'.hh':  "sourcecode.cpp.h",
	'.inl': "sourcecode.cpp.h",
	'.hpp': "sourcecode.cpp.h",

	'.c':   "sourcecode.c.c",

	'.m':   "sourcecode.c.objc",

	'.mm':  "sourcecode.cpp.objcpp",

	'.cc':  "sourcecode.cpp.cpp",

	'.cpp': "sourcecode.cpp.cpp",
	'.C':   "sourcecode.cpp.cpp",
	'.cxx': "sourcecode.cpp.cpp",
	'.c++': "sourcecode.cpp.cpp",

	'.l':   "sourcecode.lex", # luthor
	'.ll':  "sourcecode.lex",

	'.y':   "sourcecode.yacc",
	'.yy':  "sourcecode.yacc",

	'.plist': "text.plist.xml",
	".nib":   "wrapper.nib",
	".xib":   "text.xib",
}

# Used in PBXNativeTarget elements
PRODUCT_TYPE_APPLICATION = 'com.apple.product-type.application'
PRODUCT_TYPE_FRAMEWORK = 'com.apple.product-type.framework'
PRODUCT_TYPE_TOOL = 'com.apple.product-type.tool'
PRODUCT_TYPE_LIB_STATIC = 'com.apple.product-type.library.static'
PRODUCT_TYPE_LIB_DYNAMIC = 'com.apple.product-type.library.dynamic'
PRODUCT_TYPE_EXTENSION = 'com.apple.product-type.kernel-extension'
PRODUCT_TYPE_IOKIT = 'com.apple.product-type.kernel-extension.iokit'

# Used in PBXFileReference elements
FILE_TYPE_APPLICATION = 'wrapper.cfbundle'
FILE_TYPE_FRAMEWORK = 'wrapper.framework'

TARGET_TYPE_FRAMEWORK = (PRODUCT_TYPE_FRAMEWORK, FILE_TYPE_FRAMEWORK, '.framework')
TARGET_TYPE_APPLICATION = (PRODUCT_TYPE_APPLICATION, FILE_TYPE_APPLICATION, '.app')

TARGET_TYPES = {
	'framework': TARGET_TYPE_FRAMEWORK,
	'app': TARGET_TYPE_APPLICATION
}

class XcodeConfiguration(Configure.ConfigurationContext):
	""" Configuration of the project """
	def __init__(self):
		Configure.ConfigurationContext.__init__(self)

	def execute(self):

		# Run user configure()
		Context.Context.execute(self)
		
		if not self.env.PROJ_CONFIGURATION:
			self.to_log("A default project configuration was created since no custom one was given in the configure(ctx) stage. Define your custom project settings by adding PROJ_CONFIGURATION to env. The env.PROJ_CONFIGURATION must be a dictionary with at least one key, where each key is the configuration name, and the value is a dictionary of key/value settings.\n")

		# Create default project configuration?
		# if 'PROJ_CONFIGURATION' not in self.env.keys():
		self.env.PROJ_CONFIGURATION = {
			"Debug": self.env.get_merged_dict(),
			"Release": self.env.get_merged_dict(),
		}

		# Run user configuration(ctx) for customization
		Configure.ConfigurationContext.execute(self)

		# Error check customization
		if not isinstance(self.env.PROJ_CONFIGURATION, dict):
			raise Errors.ConfigurationError("The env.PROJ_CONFIGURATION must be a dictionary with at least one key, where each key is the configuration name, and the value is a dictionary of key/value settings.")



part1 = 0
part2 = 10000
part3 = 0
id = 562000999
def newid():
	global id
	id = id + 1
	return "%04X%04X%04X%012d" % (0, 10000, 0, id)

class XCodeNode:
	def __init__(self):
		self._id = newid()
		self._been_written = False

	def tostring(self, value):
		if isinstance(value, dict):
			result = "{\n"
			for k,v in value.items():
				result = result + "\t\t\t%s = %s;\n" % (k, self.tostring(v))
			result = result + "\t\t}"
			return result
		elif isinstance(value, str):
			return "\"%s\"" % value
		elif isinstance(value, list):
			result = "(\n"
			for i in value:
				result = result + "\t\t\t%s,\n" % self.tostring(i)
			result = result + "\t\t)"
			return result
		elif isinstance(value, XCodeNode):
			return value._id
		else:
			return str(value)

	def write_recursive(self, value, file):
		if isinstance(value, dict):
			for k,v in value.items():
				self.write_recursive(v, file)
		elif isinstance(value, list):
			for i in value:
				self.write_recursive(i, file)
		elif isinstance(value, XCodeNode):
			value.write(file)

	def write(self, file):
		if not self._been_written:
			self._been_written = True
			for attribute,value in self.__dict__.items():
				if attribute[0] != '_':
					self.write_recursive(value, file)
			w = file.write
			w("\t%s = {\n" % self._id)
			w("\t\tisa = %s;\n" % self.__class__.__name__)
			for attribute,value in self.__dict__.items():
				if attribute[0] != '_':
					w("\t\t%s = %s;\n" % (attribute, self.tostring(value)))
			w("\t};\n\n")

class XCID(XCodeNode):
	def __init__(self, id):
	    self._id = id
	def write(self, file):
		pass


# Configurations
class XCBuildConfiguration(XCodeNode):
	def __init__(self, name, settings = {}, env=None):
		XCodeNode.__init__(self)
		self.baseConfigurationReference = ""
		self.buildSettings = settings
		self.name = name
		if env and env.ARCH:
			settings['ARCHS'] = " ".join(env.ARCH)


class XCConfigurationList(XCodeNode):
	def __init__(self, settings):
		XCodeNode.__init__(self)
		self.buildConfigurations = settings
		self.defaultConfigurationIsVisible = 0
		self.defaultConfigurationName = settings and settings[0].name or ""

# Group/Files
class PBXFileReference(XCodeNode):
	def __init__(self, name, path, filetype = '', sourcetree = "SOURCE_ROOT"):
		XCodeNode.__init__(self)
		self.fileEncoding = 4
		if not filetype:
			_, ext = os.path.splitext(name)
			filetype = MAP_EXT.get(ext, 'text')
		self.lastKnownFileType = filetype
		self.name = name
		self.path = path
		self.sourceTree = sourcetree

class PBXBuildFile(XCodeNode):
	""" This element indicate a file reference that is used in a PBXBuildPhase (either as an include or resource). """
	def __init__(self, fileRef, settings={}):
		XCodeNode.__init__(self)
		
		# fileRef is a reference to a PBXFileReference object
		self.fileRef = fileRef

		# A map of key/value pairs for additionnal settings.
		self.settings = settings
		

class PBXGroup(XCodeNode):
	def __init__(self, name, sourcetree = "<group>"):
		XCodeNode.__init__(self)
		self.children = []
		self.name = name
		self.sourceTree = sourcetree

	def add(self, root, sources):
		folders = {}
		def folder(n):
			if not n.is_child_of(root):
				return self
			try:
				return folders[n]
			except KeyError:
				f = PBXGroup(n.name)
				p = folder(n.parent)
				folders[n] = f
				p.children.append(f)
				return f
		self.children.extend(sources)
		return
		for s in sources:
			# f = folder(s.parent)

			source = PBXFileReference(s.name, s.abspath())
			self.children.append(source)
			# f.children.append(source)

class PBXContainerItemProxy(XCodeNode):
	""" This is the element for to decorate a target item. """
	def __init__(self, containerPortal, remoteGlobalIDString, remoteInfo='', proxyType=1):
		XCodeNode.__init__(self)
		self.containerPortal = containerPortal # PBXProject
		self.remoteGlobalIDString = remoteGlobalIDString # PBXNativeTarget
		self.remoteInfo = remoteInfo # Target name
		self.proxyType = proxyType
		

class PBXTargetDependency(XCodeNode):
	""" This is the element for referencing other target through content proxies. """
	def __init__(self, native_target, proxy):
		XCodeNode.__init__(self)
		self.target = native_target
		self.targetProxy = proxy
		

# Framework sources
class PBXFrameworksBuildPhase(XCodeNode):
	""" This is the element for the framework link build phase, i.e. linking to frameworks """
	def __init__(self, pbxbuildfiles):
		XCodeNode.__init__(self)
		self.buildActionMask = 2147483647
		self.runOnlyForDeploymentPostprocessing = 0
		self.files = pbxbuildfiles #List of PBXBuildFile (.o, .framework, .dylib)


# Compile Sources
class PBXSourcesBuildPhase(XCodeNode):
	""" Represents the 'Compile Sources' build phase in a Xcode target """
	def __init__(self, buildfiles):
		XCodeNode.__init__(self)
		self.files = buildfiles # List of PBXBuildFile objects

# Targets
class PBXLegacyTarget(XCodeNode):
	def __init__(self, action, target=''):
		XCodeNode.__init__(self)
		self.buildConfigurationList = XCConfigurationList([XCBuildConfiguration('waf', {})])
		if not target:
			self.buildArgumentsString = "%s %s" % (sys.argv[0], action)
		else:
			self.buildArgumentsString = "%s %s --targets=%s" % (sys.argv[0], action, target)
		self.buildPhases = []
		self.buildToolPath = sys.executable
		self.buildWorkingDirectory = ""
		self.dependencies = []
		self.name = target or action
		self.productName = target or action
		self.passBuildSettingsInEnvironment = 0

class PBXShellScriptBuildPhase(XCodeNode):
	def __init__(self, action, target):
		XCodeNode.__init__(self)
		self.buildActionMask = 2147483647
		self.files = []
		self.inputPaths = []
		self.outputPaths = []
		self.runOnlyForDeploymentPostProcessing = 0
		self.shellPath = "/bin/sh"
		self.shellScript = "%s %s %s --targets=%s" % (sys.executable, sys.argv[0], action, target)

class PBXNativeTarget(XCodeNode):
	def __init__(self, target, node, buildphases, configlist, target_type=TARGET_TYPE_APPLICATION):
		XCodeNode.__init__(self)

		product_type = target_type[0]
		file_type = target_type[1]

		self.buildConfigurationList = configlist
		self.buildPhases = buildphases
		self.buildRules = []
		self.dependencies = []
		self.name = target
		self.productName = target
		self.productType = product_type # See TARGET_TYPE_ tuples constants
		self.productReference = PBXFileReference(target, node.abspath(), file_type, '')

# Root project object
class PBXProject(XCodeNode):
	def __init__(self, name, version, env):
		XCodeNode.__init__(self)

		if not isinstance(env.PROJ_CONFIGURATION, dict):
			raise Errors.WafError("env.PROJ_CONFIGURATION is not a dictionary. Did you import the xcode module in your wscript?")

		# Retreive project configuration
		configurations = []
		for config_name, settings in env.PROJ_CONFIGURATION.items():
			cf = XCBuildConfiguration(config_name, settings)
			configurations.append(cf)

		self.buildConfigurationList = XCConfigurationList(configurations)
		self.compatibilityVersion = version[0]
		self.hasScannedForEncodings = 1;
		self.mainGroup = PBXGroup(name)
		self.projectRoot = ""
		self.projectDirPath = ""
		self.targets = []
		self._objectVersion = version[1]
		self._output = {}

	def write(self, file):
		if self._been_written:
			return
		w = file.write
		w("// !$*UTF8*$!\n")
		w("{\n")
		w("\tarchiveVersion = 1;\n")
		w("\tclasses = {\n")
		w("\t};\n")
		w("\tobjectVersion = %d;\n" % self._objectVersion)
		w("\tobjects = {\n\n")

		XCodeNode.write(self, file)

		w("\t};\n")
		w("\trootObject = %s;\n" % self._id)
		w("}\n")

	def add_task_gen(self, target):
		self.targets.append(target)
		self._output[target.name] = target

class xcode(Build.BuildContext):
	cmd = 'xcode'
	fun = 'build'

	def collect_source(self, tg):
		source_files = tg.to_nodes(getattr(tg, 'source', []))
		plist_files = tg.to_nodes(getattr(tg, 'mac_plist', []))
		resource_files = [tg.path.find_node(i) for i in Utils.to_list(getattr(tg, 'mac_resources', []))]
		include_dirs = Utils.to_list(getattr(tg, 'includes', [])) + Utils.to_list(getattr(tg, 'export_dirs', []))
		include_files = []
		for x in include_dirs:
			if not isinstance(x, str):
				include_files.append(x)
				continue
			d = tg.path.find_node(x)
			if d:
				lst = [y for y in d.ant_glob(HEADERS_GLOB, flat=False)]
				include_files.extend(lst)

		# remove duplicates
		source = list(set(source_files + plist_files + resource_files + include_files))
		source.sort(key=lambda x: x.abspath())
		return source

	def execute(self):
		"""
		Entry point
		"""
		self.restore()
		if not self.all_envs:
			self.load_envs()
		self.recurse([self.run_dir])

		appname = getattr(Context.g_module, Context.APPNAME, os.path.basename(self.srcnode.abspath()))

		buildsettings = self.env.get_merged_dict()
		buildsettings.update()

		p = PBXProject(appname, ('Xcode 3.2', 46), self.env)

		for g in self.groups:
			for tg in g:
				if not isinstance(tg, TaskGen.task_gen):
					continue

				tg.post()

				sources = [PBXFileReference(n.name, n.abspath()) for n in self.collect_source(tg)]
				group = PBXGroup(tg.name)
				group.add(tg.path, sources)
				p.mainGroup.children.append(group)
				
				buildfiles = [PBXBuildFile(fileref) for fileref in group.children]
				compilesources = PBXSourcesBuildPhase(buildfiles)
				buildphases = [compilesources]


				target_type = getattr(tg, 'target_type', '')
				if target_type not in TARGET_TYPES:
					raise Errors.WafError("Target type %s does not exists. Available options are %s. In target %s" % (target_type, ', '.join(TARGET_TYPES.keys()), tg.name))
				file_ext = target_type[2]
				target_node = tg.path.find_or_declare(tg.name+file_ext)

				# Check if any framework to link against is some other target we've made
				dependency_targets = []
				framework = getattr(tg, 'link_framework', [])
				for fw in framework:
					if fw and fw in p._output:
						# Target framework found. Make a build file of it
						target = p._output[fw]
						product = PBXBuildFile(target.productReference)
						fw = PBXFrameworksBuildPhase([product])
						buildphases.append(fw)

						# Create an XCode dependency so that it knows to build that framework before this target
						proxy = PBXContainerItemProxy(p, target, target.name)
						dependecy = PBXTargetDependency(target, proxy)
						dependency_targets.append(dependecy)

				
				# Create settings which can override the project settings. Defaults to none if user
				# did not pass argument.
				settings = getattr(tg, 'settings', {})
				cflst = []
				for k,v in settings.items():
					cflst.append(XCBuildConfiguration(k, v))
				cflst = XCConfigurationList(cflst)
				
				# Setup include search paths
				include_dirs = Utils.to_list(getattr(tg, 'includes', []))
				include_dirs_ = []
				for x in include_dirs:
					if not isinstance(x, str):
						d = x
					else:
						d = tg.path.find_node(x)
					include_dirs_.append(d.abspath())
				for k,v in settings.items():
					v['HEADER_SEARCH_PATHS'] = ' '.join(include_dirs_)

				target = PBXNativeTarget(tg.name, target_node, buildphases, cflst, target_type)
				target.dependencies.extend(dependency_targets)

				p.add_task_gen(target)
				
		node = self.bldnode.make_node('%s.xcodeproj' % appname)
		node.mkdir()
		node = node.make_node('project.pbxproj')
		p.write(open(node.abspath(), 'w'))
		


