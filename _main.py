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

g_engine_path_map = {}
g_engine_shader_path_set = set()


def log(channel, text):
	# type: (str, str) -> None
	if LOG:
		print("[%s]: %s" % (channel, text))
	else:
		pass
	pass


def info(text):
	log(INFO, text)
	pass


def error(text):
	log(ERROR, text)
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


# noinspection PyMethodMayBeStatic
class UnrealShaderEventListener(sublime_plugin.EventListener):

	STATUS_KEY = "UnrealShaderRoot"

	def __init__(self):
		super(UnrealShaderEventListener, self).__init__()
		pass

	def on_pre_close(self, view):
		window = view.window()
		#
		global g_engine_shader_path_set
		# 最后的窗格
		if len(window.views()) == 1:
			info("Last view. Cleaning shader folder.")
			data = view.window().project_data()
			if "folders" in data:
				clear_folders = []
				for folder_dict in data["folders"]:
					print(folder_dict["path"], g_engine_shader_path_set)
					if "path" in folder_dict and folder_dict["path"] in g_engine_shader_path_set:
						info("Remove shader folder: %s" % folder_dict["path"])
					else:
						clear_folders.append(folder_dict)
				print(clear_folders)
				data["folders"] = clear_folders
				view.window().set_project_data(data)
		pass

	def on_activated(self, view):
		#
		global g_engine_path_map
		#
		current_filepath = view.file_name()
		#
		if Utils.support(current_filepath):
			#
			if current_filepath not in g_engine_path_map:
				engine_path = Utils.get_engine_path(current_filepath)
				if engine_path:
					info("Found engine path: %s" % engine_path)
					g_engine_path_map[current_filepath] = engine_path
					g_engine_shader_path_set.add(Utils.get_engine_shader_path(engine_path))
				else:
					info("Empty engine path!!!")
					return
			else:
				engine_path = g_engine_path_map[current_filepath]
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
				info("Open engine shader folder automatically.")
		pass


# noinspection PyMethodMayBeStatic
class IntelliJumpCommand(sublime_plugin.TextCommand):

	INCLUDE_MACRO = "#include"
	INCLUDE_SCOPE = "meta.preprocessor.include.us"

	def __init__(self, *args, **kwargs):
		super(IntelliJumpCommand, self).__init__(*args, **kwargs)
		self.mouse_vector = (0, 0)
		pass

	def run(self, _edit, event=None):
		self.update_mouse_point(event)
		self.goto_file(self.current_cursor_line_text())
		pass

	def want_event(self):
		return True

	def is_visible(self, event=None):
		self.update_mouse_point(event)
		if self.can_goto_file(self.current_cursor_line_text()) is not None:
			return True
		return False

	def update_mouse_point(self, event):
		if event is not None:
			self.mouse_vector = (event['x'], event['y'])
		pass

	def current_edit_line_text(self):
		# type: () -> str
		return self.view.substr(self.view.line(self.view.sel()[-1].b))

	def current_cursor_line_text(self):
		# type: () -> str
		point = self.view.window_to_text(self.mouse_vector)
		return self.view.substr(self.view.line(point))

	def can_goto_file(self, text_line):
		# type: (str) -> str or None
		#
		global g_engine_path_map
		#
		words = text_line.split()
		#
		if len(words) == 2 and words[0] == self.INCLUDE_MACRO:
			return words[1][1:-1]
		else:
			return None
		pass

	def can_goto_definition(self, _text_line):
		# type: (str) -> str or None
		return None

	def goto_file(self, text_line):
		#
		global g_engine_path_map
		#
		filename = self.can_goto_file(text_line)
		if filename is not None:
			#
			current_filepath = self.view.file_name()
			#
			info("Jump to include: %s -> %s" % (current_filepath, filename))
			#
			if current_filepath in g_engine_path_map:
				engine_path = g_engine_path_map[current_filepath]
				if engine_path:
					virtual_filepath = filename
					abs_filepath = Utils.get_shader_file_path(current_filepath, virtual_filepath, engine_path)
					if abs_filepath:
						self.view.window().open_file(abs_filepath)
					else:
						error("Failed to search: %s" % filename)
				else:
					error("Not exist engine path for: %s" % current_filepath)
		pass

	def goto_definition(self, text_line):
		pass


# noinspection PyMethodMayBeStatic
class IntelliJumpByKeyCommand(IntelliJumpCommand):

	def run(self, _edit, event=None):
		if self.can_goto_file(self.current_edit_line_text()):
			self.goto_file(self.current_edit_line_text())
		else:
			self.view.window().run_command("goto_definition")
		pass
