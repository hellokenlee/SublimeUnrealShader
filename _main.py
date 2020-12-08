# -*- coding:UTF-8 -*-
__author__ = "KenLee"
__email__ = "hellokenlee@163.com"


import os
import json
import subprocess

import sublime
import sublime_plugin

LOG = True
INFO = "Info"
ERROR = "Error"

engine_path_map = {}


def log(channel, text):
	# type: (str, str) -> None
	if LOG:
		print("[%s]: %s" % (channel, text))
	else:
		pass
	pass


class Utils(object):

	UPROJ = ".uproject"
	EXTENSIONS = [".usf", ".ush"]
	ENGINE_SHADERS_PATH = os.path.join("Engine", "Shaders")

	@classmethod
	def support(cls, filepath):
		# type: (basestring) -> bool
		if filepath:
			for extens in cls.EXTENSIONS:
				if filepath.endswith(extens):
					return True
		return False

	@classmethod
	def get_shader_file_path(cls, current, include, engine):
		# type: (str, str, str) -> str
		# 同目录下的文件
		if not include.startswith("/"):
			shader_filepath = os.path.join(os.path.dirname(current), include)
			shader_filepath = os.path.normpath(shader_filepath)
			if os.path.exists(shader_filepath):
				return shader_filepath
		# 引擎着色器目录下的文件
		if include.startswith("/Engine"):
			shader_dir = cls.get_engine_shader_path(engine)
			shader_filepath = os.path.normpath(include.replace("/Engine", shader_dir))
			if os.path.exists(shader_filepath):
				return shader_filepath
		#
		return ""

	@classmethod
	def get_engine_path(cls, spath):
		# type: (str) -> basestring
		# 如果传入的是文件
		if os.path.isfile(spath):
			return cls.get_engine_path(os.path.dirname(spath))
		# 找到根目录也没找到
		if os.path.dirname(spath) == spath:
			return ""
		# 如果已经在引擎目录
		if spath.endswith(cls.ENGINE_SHADERS_PATH):
			return os.path.dirname(spath)
		# 寻找当前目录的项目文件
		filelist = os.listdir(spath)
		for filename in filelist:
			if filename.endswith(cls.UPROJ):
				#
				filepath = os.path.join(spath, filename)
				#
				with open(filepath, "r") as fp:
					uproject = json.load(fp)
					if "EngineAssociation" in uproject:
						return cls.guid_to_path(str(uproject["EngineAssociation"]))
		#
		return cls.get_engine_path(os.path.dirname(spath))

	@staticmethod
	def get_engine_shader_path(epath):
		return os.path.normpath(os.path.join(epath, "Shaders"))

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
			if current_filepath not in engine_path_map:
				engine_path = Utils.get_engine_path(current_filepath)
				if engine_path:
					print("Found engine path: %s" % engine_path)
					engine_path_map[current_filepath] = engine_path
				else:
					print("Empty engine path!!!")
					return
			else:
				engine_path = engine_path_map[current_filepath]
			#
			view.set_status(self.STATUS_KEY, "Engine: %s\\ " % engine_path)
			#
			shaders_path = Utils.get_engine_shader_path(engine_path)
			if shaders_path not in view.window().folders():
				data = {
					"folders":
						[
							{
								"follow_symlinks": True,
								"path": shaders_path
							}
						],
				}
				view.window().set_project_data(data)
				print("Open engine shader folder automatically.")
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
			log(INFO, "Jump to include: %s -> %s" % (current_filepath, include[1][1:-1]))
			#
			if current_filepath in engine_path_map:
				engine_path = engine_path_map[current_filepath]
				if engine_path:
					virtual_filepath = include[1][1:-1]
					abs_filepath = Utils.get_shader_file_path(current_filepath, virtual_filepath, engine_path)
					if abs_filepath:
						self.view.window().open_file(abs_filepath)
					else:
						log(ERROR, "Failed to search: %s" % include[1][1:-1])
				else:
					log(ERROR, "Not exist engine path for: %s" % current_filepath)
		pass

	def jump_to_definition(self, definition):
		pass
