
import sublime
import sublime_plugin
import re
import sys
from glob import glob
from os import *
from os.path import *


INC_RE = re.compile(
    r"\s*#include\s*([\<\"])((([^/<>\"]*)/)*)([^/<>\"]*)([\>\"])")
c_include_paths = set()
cxx_include_paths = set()

DEBUG = False


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
def get_common_c_headers(folder):
    log("get_common_c_headers", folder)
    return get_headers(c_include_paths, folder)


@cache
def get_common_cxx_headers(folder):
    log("get_common_cxx_headers", folder)
    return get_headers(cxx_include_paths, folder)


def contain_header(path):
    for f in listdir(path):
        if splitext(f)[1] in [".h", ".hpp"]:
            return True
    return False


def get_user_headers(folder):
    log("get_user_headers", folder)
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
            headers.extend(get_user_headers(folder))
        if self.is_in_cxx(scope):
            headers.extend(get_common_cxx_headers(folder))
        else:
            headers.extend(get_common_c_headers(folder))
        log(headers[:10])
        return headers


def get_environ_paths(key):
    return [join(p, '') for p in environ[key].split(';')]


def plugin_loaded():
    for paths in map(get_environ_paths, ["INCLUDE"]):
        c_include_paths.update(paths)
        cxx_include_paths.update(paths)
    for paths in map(get_environ_paths, ["C_INCLUDE_PATH"]):
        c_include_paths.update(paths)
    for paths in map(get_environ_paths, ["CPLUS_INCLUDE_PATH"]):
        cxx_include_paths.update(paths)
    log(c_include_paths)
    log(cxx_include_paths)
