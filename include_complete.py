
import sublime
import sublime_plugin
import re
import sys
from glob import glob
from os import listdir
from os.path import isdir

DEBUG = False

INC_RE = re.compile(
    r"\s*#include\s*([\<\"])((([^/<>\"]*)/)*)([^/<>\"]*)([\>\"])")

c_include_path = set()
cplus_include_path = set()


def log(*args, **kwds):
    if DEBUG:
        print(*args, **kwds)


def cache(func):
    pool = {}

    def wrapper(arg):
        if arg in pool:
            log("hit cache")
            return pool[arg]
        else:
            result = func(arg)
            pool[arg] = result
            return result
    return wrapper


def get_headers(paths, folder):
    folder = folder.replace('/', sep)
    headers = []
    for p in paths:
        root = join(p, folder)
        if not exists(root):
            continue
        log(p)
        for i in listdir(root):
            if i.startswith('.'):
                continue
            if isdir(join(root, i)):
                headers.append(("%s/\tfolder" % i, "%s/" % i))
            elif splitext(i)[1] in ["", ".h", ".hpp"]:
                headers.append(("%s\theader" % i, "%s" % i))
    headers.sort()
    return headers


@cache
def get_system_c_headers(folder):
    log("get_system_c_headers", folder)
    return get_headers(c_include_path, folder)


@cache
def get_system_cxx_headers(folder):
    log("get_system_cxx_headers", folder)
    return get_headers(cplus_include_path, folder)


def contain_header(path):
    for f in listdir(path):
        if splitext(f)[1] in [".h", ".hpp"]:
            return True
    return False


def get_project_headers(folder):
    log("get_project_headers", folder)
    paths = []
    for f in sublime.active_window().folders():
        paths.append(f)
        for i in listdir(f):
            path = join(f, i)
            if isdir(path) and not i.startswith('.'):
                paths.append(path)
    paths = filter(contain_header, paths)
    return get_headers(paths, folder)


class IncludeCompleteListenner(sublime_plugin.EventListener):

    def should_trigger(self, scope):
        selector = "meta.preprocessor.c.include"
        log(scope, sublime.score_selector(scope, selector))
        return sublime.score_selector(scope, selector)

    def is_in_cxx(self, scope):
        selector = "source.c++"
        log(scope, sublime.score_selector(scope, selector))
        return sublime.score_selector(scope, selector)

    def on_query_completions(self, view, prefix, locations):
        scope = view.scope_name(locations[0])
        if not self.should_trigger(scope):
            return

        region = view.line(locations[0])
        line = view.substr(region)

        match = INC_RE.match(line)
        if match is None:
            return

        surround = match.group(1)
        folder = match.group(2)
        prefix = match.group(3)
        log(folder)

        headers = []
        if surround == '\"':
            headers.extend(get_project_headers(folder))
        if self.is_in_cxx(scope):
            headers.extend(get_system_cxx_headers(folder))
        else:
            headers.extend(get_system_c_headers(folder))
        log(headers[:10])
        return headers


def plugin_loaded():
    for settings_name in ["IncludeComplete.sublime-settings",
                          "IncludeComplete ({}).sublime-settings".format(
                              sublime.platform().capitalize())]:
        settings = sublime.load_settings(settings_name)
        get_setting = lambda key: settings.get(key, [])
        for paths in map(get_setting, ["include"]):
            c_include_path.update(paths)
            cplus_include_path.update(paths)
        for paths in map(get_setting, ["c_include_path"]):
            c_include_path.update(paths)
        for paths in map(get_setting, ["cplus_include_path"]):
            cplus_include_path.update(paths)
    log(c_include_path)
    log(cplus_include_path)
