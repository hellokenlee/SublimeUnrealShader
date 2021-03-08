# -*- coding:UTF-8 -*-
__author__ = "KenLee"
__email__ = "hellokenlee@163.com"


import os
import json
import copy
import subprocess

import sublime
import sublime_plugin

LOG = True
INFO = "Info"
ERROR = "Error"

g_view_id_to_folder_paths = {}


def log(channel, text):
	# type: (str, str) -> None
	if LOG:
		print("UnrealShader: [%s]: %s" % (channel, text))
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

	UPLUGIN = ".uplugin"
	UPROJECT = ".uproject"
	EXTENSIONS = [".usf", ".ush"]
	ENGINE_FOLDER_NAME = "Engine"
	SHADERS_FOLDER_NAME = "Shaders"

	@classmethod
	def support(cls, filepath):
		# type: (basestring) -> bool
		if filepath:
			for extens in cls.EXTENSIONS:
				if filepath.endswith(extens):
					return True
		return False

	@classmethod
	def get_shader_file_path(cls, current, include, root):
		# type: (str, str, str) -> str
		# Same directory files
		if not include.startswith("/"):
			shader_filepath = os.path.join(os.path.dirname(current), include)
			shader_filepath = os.path.normpath(shader_filepath)
			if os.path.exists(shader_filepath):
				return shader_filepath
		# Files below engines
		if include.startswith("/Engine"):
			shader_filepath = os.path.normpath(include.replace("/Engine", root))
			if os.path.exists(shader_filepath):
				return shader_filepath
		#
		return ""

	@classmethod
	def get_engine_path(cls, some_path):
		# type: (str) -> basestring
		# Failed to find in root
		if os.path.dirname(some_path) == some_path:
			return ""
		# Search up if it is a file
		if os.path.isfile(some_path):
			return cls.get_engine_path(os.path.dirname(some_path))
		# Return if it is an engine folder
		if os.path.basename(some_path) == cls.ENGINE_FOLDER_NAME:
			return some_path
		# Return related engine folder if it is a project folder
		filelist = os.listdir(some_path)
		for filename in filelist:
			if filename.endswith(cls.UPROJECT):
				#
				filepath = os.path.join(some_path, filename)
				#
				with open(filepath, "r") as fp:
					uproject = json.load(fp)
					if "EngineAssociation" in uproject:
						return cls.guid_to_path(str(uproject["EngineAssociation"]))
		# Search up if it is everything else
		return cls.get_engine_path(os.path.dirname(some_path))

	@classmethod
	def get_engine_shaders_path(cls, engine_path):
		return os.path.normpath(os.path.join(engine_path, cls.SHADERS_FOLDER_NAME))

	@classmethod
	def get_plugin_shaders_path(cls, some_path):
		# type: (str) -> basestring
		# Failed to find in root
		if os.path.dirname(some_path) == some_path:
			return ""
		# Search up if it is a file
		if os.path.isfile(some_path):
			return cls.get_plugin_shaders_path(os.path.dirname(some_path))
		# Return if it is a plugin folder
		filelist = os.listdir(some_path)
		for filename in filelist:
			if filename.endswith(cls.UPLUGIN):
				shaders_path = os.path.join(some_path, cls.SHADERS_FOLDER_NAME)
				if os.path.exists(shaders_path):
					return shaders_path
				break
		return cls.get_plugin_shaders_path(os.path.dirname(some_path))

	@classmethod
	def add_view_folder_path(cls, view, path):
		global g_view_id_to_folder_paths
		path = os.path.normpath(path)
		return g_view_id_to_folder_paths.setdefault(view.id(), set()).add(path)

	@classmethod
	def get_view_all_folder_paths(cls, view):
		global g_view_id_to_folder_paths
		return copy.deepcopy(g_view_id_to_folder_paths.get(view.id(), set()))

	@classmethod
	def open_project_folder(cls, view, folder_path, rename):
		#
		cls.add_view_folder_path(view, folder_path)
		#
		window = view.window()
		if window is None:
			return
		#
		if folder_path not in window.folders():
			# Get proj
			data = window.project_data()
			data = {} if data is None else data
			# Open folder
			folders_data = data.setdefault("folders", [])
			folders_data.append(
				{
					"follow_symlinks": True,
					"path": folder_path,
					"name": rename,
				}
			)
			#
			window.set_project_data(data)
		pass

	@classmethod
	def close_project_folder(cls, view):
		#
		window = view.window()
		if window is None:
			return
		#
		for folder_path in Utils.get_view_all_folder_paths(view):
			if folder_path in window.folders():
				# Get proj
				data = window.project_data()
				if data is None:
					return
				# Check if should alive
				for other_view in window.views():
					if view.id() == other_view.id():
						continue
					related_folder_paths = Utils.get_view_all_folder_paths(other_view)
					if folder_path in related_folder_paths:
						print(related_folder_paths, folder_path)
						return
				# Close if none view related to this folder
				remain_folders = []
				for folder_dict in data.get("folders", {}):
					if folder_path == folder_dict["path"]:
						info("Remove shader folder: %s" % folder_dict["path"])
					else:
						remain_folders.append(folder_dict)
				data["folders"] = remain_folders
				window.set_project_data(data)
		pass

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
		Utils.close_project_folder(view)
		pass

	def on_activated(self, view):
		#
		current_filepath = view.file_name()
		#
		if Utils.support(current_filepath):
			#
			engine_path = Utils.get_engine_path(current_filepath)
			engine_shaders_path = Utils.get_engine_shaders_path(engine_path)
			plugin_shaders_path = Utils.get_plugin_shaders_path(current_filepath)
			#
			view.set_status(self.STATUS_KEY, "Engine: %s\\ " % engine_path)
			#
			if view.settings().get('AutoOpenShaderFolder'):
				if engine_shaders_path:
					Utils.open_project_folder(view, engine_shaders_path, "Shaders (Engine)")
					info("Open engine shader folder automatically: %s" % engine_shaders_path)
				if plugin_shaders_path:
					Utils.open_project_folder(view, plugin_shaders_path, "Shaders (Plugin)")
					info("Open plugin shader folder automatically: %s" % plugin_shaders_path)
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
		include_filename = self.can_goto_file(text_line)
		if include_filename is not None:
			#
			current_filepath = self.view.file_name()
			#
			info("Try jump to include: %s -> %s" % (current_filepath, include_filename))
			#
			shaders_folder_paths = Utils.get_view_all_folder_paths(self.view)
			#
			for folder_path in shaders_folder_paths:
				abs_filepath = Utils.get_shader_file_path(current_filepath, include_filename, folder_path)
				if abs_filepath:
					self.view.window().open_file(abs_filepath)
					return
			#
			info("Failed to search: %s" % include_filename)
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
