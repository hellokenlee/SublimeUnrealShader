# -*- coding:UTF-8 -*-
__author__ = "KenLee"
__email__ = "hellokenlee@163.com"


import os
import json
import subprocess

import sublime
import sublime_plugin


engine_path_map = {}


class Utils(object):

	UPROJ = ".uproject"
	EXTENSIONS = [".usf", ".ush"]
	ENGINE_SUB_PATH = os.path.join("UnrealEngine", "Engine", "Shader")

	@staticmethod
	def support(filepath):
		# type: (basestring) -> bool
		if filepath:
			for extens in Utils.EXTENSIONS:
				if filepath.endswith(extens):
					return True
		return False

	@staticmethod
	def get_shader_file_path(virtual_path, engine_path):
		# type: (str, str) -> str
		shader_dir = Utils.get_engine_shader_path(engine_path)
		return os.path.normpath(virtual_path.replace("/Engine", shader_dir))

	@staticmethod
	def get_engine_path(spath):
		# type: (str) -> basestring
		# 如果传入的是文件
		if os.path.isfile(spath):
			return Utils.get_engine_path(os.path.dirname(spath))
		# 找到根目录也没找到
		if os.path.dirname(spath) == spath:
			return ""
		# 如果已经在引擎目录
		if Utils.ENGINE_SUB_PATH in spath:
			while os.path.basename(spath) != "UnrealEngine":
				spath = os.path.dirname(spath)
			return spath
		# 寻找当前目录的项目文件
		filelist = os.listdir(spath)
		for filename in filelist:
			if filename.endswith(Utils.UPROJ):
				#
				filepath = os.path.join(spath, filename)
				#
				with open(filepath, "r") as fp:
					uproject = json.load(fp)
					if "EngineAssociation" in uproject:
						return Utils.guid_to_path(str(uproject["EngineAssociation"]))
		#
		return Utils.get_engine_path(os.path.dirname(spath))

	@staticmethod
	def get_engine_shader_path(epath):
		return os.path.normpath(os.path.join(epath, "Engine", "Shaders"))

	@staticmethod
	def guid_to_path(guid):
		# type: (basestring) -> basestring
		command = ['REG', 'QUERY', 'HKEY_CURRENT_USER\\Software\\Epic Games\\Unreal Engine\\Builds', '/v', guid]
		try:
			result = subprocess.check_output(command)
			result = result.decode('gbk')
			engine_path = result.split()[-1]
			return os.path.normpath(engine_path)
		except Exception as _e:
			pass
		return ""


class UnrealShaderEventListener(sublime_plugin.EventListener):

	STATUS_KEY = "UnrealShaderRoot"

	def __init__(self):
		super(UnrealShaderEventListener, self).__init__()
		pass

	def on_activated(self, view):
		#
		global engine_path_map
		#
		current_filepath = view.file_name()
		#
		if Utils.support(current_filepath):
			#
			engine_path_map.pop(current_filepath, "")
			#
			if current_filepath not in engine_path_map:
				engine_path = Utils.get_engine_path(current_filepath)
				engine_path_map[current_filepath] = engine_path
			else:
				engine_path = engine_path_map[current_filepath]
			#
			view.set_status(self.STATUS_KEY, "Engine: %s" % engine_path)
		pass


# noinspection PyMethodMayBeStatic
class IntelliJumpCommand(sublime_plugin.TextCommand):

	INCLUDE_SCOPE = "meta.preprocessor.include.us"

	def run(self, _edit):
		point = self.view.sel()[-1].b
		scopes = self.view.scope_name(point)
		scopes = scopes.split(" ")
		for scope in scopes:
			if scope == self.INCLUDE_SCOPE:
				include = self.view.substr(self.view.line(point))
				self.jump_to_include(include)
		pass

	def jump_to_include(self, include):
		#
		global engine_path_map
		#
		include = include.split()
		#
		if len(include) == 2 and include[0] == "#include":
			#
			current_filepath = self.view.file_name()
			#
			if current_filepath in engine_path_map:
				engine_path = engine_path_map[current_filepath]
				if engine_path:
					virtual_filepath = include[1][1:-1]
					self.view.window().open_file(Utils.get_shader_file_path(virtual_filepath, engine_path))
		pass

	def jump_to_definition(self, definition):
		pass
