# -*- coding:UTF-8 -*-
__author__ = "KenLee"
__email__ = "hellokenlee@163.com"

import sublime
import sublime_plugin


class IntelliJumpCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		print("IntelliJumpCommand")
		pass


class OpenIncludeFileCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		print("OpenIncludeFileCommand")
		pass


class JumpToDefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		print("JumpToDefinitionCommand")
	pass
